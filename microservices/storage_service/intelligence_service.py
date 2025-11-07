"""
Storage Service - Intelligence Service

智能文档分析服务 - 集成isA_MCP的digital_analytics_tools
"""

import logging
import httpx
import requests
import uuid
import time
import json
import os
from typing import List, Optional, Dict, Any

from .intelligence_repository import IntelligenceRepository
from core.config_manager import ConfigManager
from .intelligence_models import (
    IndexedDocument, SearchResult, DocumentStatus, ChunkingStrategy,
    SemanticSearchRequest, SemanticSearchResponse,
    RAGQueryRequest, RAGQueryResponse, RAGAnswer, RAGMode,
    IntelligenceStats
)

logger = logging.getLogger(__name__)


class IntelligenceService:
    """智能文档分析服务 - 通过MCP调用isA_MCP的digital_analytics_tools"""

    def __init__(self, config: Optional[ConfigManager] = None):
        self.repository = IntelligenceRepository(config=config)

        # isA_MCP服务端点 (default port is 8081)
        self.mcp_endpoint = os.getenv("MCP_ENDPOINT", "http://localhost:8081")

    # ==================== Helper Method for SSE Parsing ====================

    def _parse_sse_response(self, response_text: str) -> Optional[Dict[str, Any]]:
        """
        Parse Server-Sent Events (SSE) response format

        SSE 格式: data: {jsonrpc response}
        提取 result.content[0].text 并解析为最终数据

        注意: MCP 会先发送 notifications/message 进度通知，需要跳过这些，找到真正的 result

        Returns:
            解析后的响应数据（已从 MCP wrapper 中提取）
        """
        lines = response_text.strip().split('\n')
        for line in lines:
            if line.startswith('data: '):
                try:
                    # 解析 SSE data 行
                    sse_data = json.loads(line[6:])

                    # 跳过 MCP 通知消息 (method: notifications/message)
                    if sse_data.get('method') == 'notifications/message':
                        logger.debug(f"Skipping MCP notification: {sse_data.get('params', {}).get('data')}")
                        continue

                    # MCP 响应格式: {result: {content: [{text: "..."}]}}
                    if 'result' in sse_data and 'content' in sse_data['result']:
                        content = sse_data['result']['content']
                        if content and len(content) > 0:
                            # 提取 text 内容并解析为 JSON
                            text_content = content[0].get('text', '{}')
                            return json.loads(text_content)

                    # 如果不是 MCP 格式，直接返回
                    if 'result' in sse_data or 'error' in sse_data:
                        return sse_data

                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse SSE data: {e}")
                    continue

        logger.error("No valid result found in SSE response")
        return None

    # ==================== 文档索引 ====================

    async def index_file(
        self,
        file_id: str,
        user_id: str,
        organization_id: Optional[str],
        file_name: str,
        file_content: str,
        file_type: str,
        file_size: int,
        chunking_strategy: ChunkingStrategy = ChunkingStrategy.SEMANTIC,
        metadata: Optional[Dict[str, Any]] = None,
        tags: Optional[List[str]] = None
    ) -> IndexedDocument:
        """索引文件 - 在文件上传时自动调用"""
        try:
            # 检查是否已索引
            existing = await self.repository.get_by_file_id(file_id, user_id)
            if existing and existing.status == DocumentStatus.INDEXED:
                logger.info(f"File already indexed: {file_id}")
                return existing

            # 创建索引记录
            doc_id = f"doc_{uuid.uuid4().hex[:12]}"

            doc_data = IndexedDocument(
                doc_id=doc_id,
                file_id=file_id,
                user_id=user_id,
                organization_id=organization_id,
                title=file_name,
                content_preview=file_content[:200] if file_content else "",
                status=DocumentStatus.PROCESSING,
                chunking_strategy=chunking_strategy,
                chunk_count=0,
                metadata=metadata or {},
                tags=tags or []
            )

            doc_record = await self.repository.create_index_record(doc_data)

            # 通过MCP索引
            try:
                chunk_count = self._index_via_mcp(
                    user_id=user_id,
                    text=file_content,
                    metadata={
                        "doc_id": doc_id,
                        "file_id": file_id,
                        "title": file_name,
                        "file_type": file_type,
                        **(metadata or {})
                    }
                )

                # 更新为已索引
                await self.repository.update_status(
                    doc_id,
                    DocumentStatus.INDEXED,
                    chunk_count=chunk_count
                )

                doc_record.status = DocumentStatus.INDEXED
                doc_record.chunk_count = chunk_count
                return doc_record

            except Exception as e:
                logger.error(f"MCP indexing failed: {e}")
                await self.repository.update_status(doc_id, DocumentStatus.FAILED)
                raise

        except Exception as e:
            logger.error(f"Error indexing file: {e}")
            raise

    def _index_via_mcp(
        self,
        user_id: str,
        text: str,
        metadata: Dict[str, Any]
    ) -> int:
        """通过MCP调用store_knowledge (JSON-RPC 2.0 format) - 使用requests同步调用"""
        try:
            # Use the exact pattern from how_to_mcp.md
            response = requests.post(
                f"{self.mcp_endpoint}/mcp",
                headers={
                    'Content-Type': 'application/json',
                    'Accept': 'application/json, text/event-stream'
                },
                json={
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "tools/call",
                    "params": {
                        "name": "store_knowledge",
                        "arguments": {
                            "user_id": user_id,
                            "text": text,
                            "metadata": metadata
                        }
                    }
                },
                timeout=60.0
            )
            
            if response.status_code == 200:
                # Parse SSE response exactly like the documentation shows
                lines = response.text.strip().split('\n')
                for line in lines:
                    if line.startswith('data: '):
                        data = json.loads(line[6:])
                        if 'result' in data:
                            content = data['result'].get('content', [])
                            if content:
                                result_data = json.loads(content[0]['text'])
                                logger.info(f"MCP store_knowledge success: {result_data.get('status')}")
                                return 1  # Default to 1 chunk
                return 1
            else:
                raise Exception(f"MCP indexing failed: {response.status_code} - {response.text}")

        except Exception as e:
            logger.error(f"Error calling MCP store_knowledge: {e}")
            raise

    # ==================== 语义搜索 ====================

    async def semantic_search(
        self,
        request: SemanticSearchRequest,
        storage_repository  # 传入storage_repository以获取文件信息
    ) -> SemanticSearchResponse:
        """语义搜索文件"""
        try:
            start_time = time.time()

            # 通过MCP搜索
            search_results = self._search_via_mcp(
                user_id=request.user_id,
                query=request.query,
                top_k=request.top_k,
                enable_rerank=request.enable_rerank
            )

            # 构建结果
            results = []
            for result in search_results:
                # 应用分数过滤
                if result.get("relevance_score", 0) < request.min_score:
                    continue

                # 获取文件信息
                file_id = result.get("metadata", {}).get("file_id", "")
                doc_id = result.get("metadata", {}).get("doc_id", "")

                # 从storage获取文件详情
                file_record = await storage_repository.get_file_by_id(file_id, request.user_id)
                if not file_record:
                    continue

                # 应用文件类型过滤
                if request.file_types:
                    if not any(ft in file_record.content_type for ft in request.file_types):
                        continue

                # 应用标签过滤
                if request.tags:
                    file_tags = file_record.metadata.get("tags", [])
                    if not any(tag in file_tags for tag in request.tags):
                        continue

                # 增加搜索计数
                if doc_id:
                    await self.repository.increment_search_count(doc_id)

                results.append(SearchResult(
                    file_id=file_id,
                    doc_id=doc_id,
                    file_name=file_record.file_name,
                    relevance_score=result.get("relevance_score", 0.0),
                    content_snippet=result.get("text", "")[:200],
                    file_type=file_record.content_type,
                    file_size=file_record.file_size,
                    metadata=file_record.metadata,
                    uploaded_at=file_record.uploaded_at,
                    download_url=file_record.download_url
                ))

            latency_ms = (time.time() - start_time) * 1000

            return SemanticSearchResponse(
                query=request.query,
                results=results,
                results_count=len(results),
                latency_ms=latency_ms
            )

        except Exception as e:
            logger.error(f"Error in semantic search: {e}")
            raise

    def _search_via_mcp(
        self,
        user_id: str,
        query: str,
        top_k: int,
        enable_rerank: bool
    ) -> List[Dict[str, Any]]:
        """通过MCP调用search_knowledge (JSON-RPC 2.0 format)"""
        try:
            # Use the exact pattern from how_to_mcp.md
            response = requests.post(
                f"{self.mcp_endpoint}/mcp",
                headers={
                    'Content-Type': 'application/json',
                    'Accept': 'application/json, text/event-stream'
                },
                json={
                    "jsonrpc": "2.0",
                    "id": 2,
                    "method": "tools/call",
                    "params": {
                        "name": "search_knowledge",
                        "arguments": {
                            "user_id": user_id,
                            "query": query,
                            "top_k": top_k,
                            "enable_rerank": enable_rerank
                        }
                    }
                },
                timeout=30.0
            )
            
            if response.status_code == 200:
                # Parse SSE response exactly like the documentation shows
                lines = response.text.strip().split('\n')
                for line in lines:
                    if line.startswith('data: '):
                        data = json.loads(line[6:])
                        if 'result' in data:
                            content = data['result'].get('content', [])
                            if content:
                                result_data = json.loads(content[0]['text'])
                                return result_data.get('data', {}).get('search_results', [])
                return []
            else:
                logger.error(f"MCP search failed: {response.status_code} - {response.text}")
                return []

        except Exception as e:
            logger.error(f"Error calling MCP search_knowledge: {e}")
            return []

    # ==================== RAG问答 ====================

    async def rag_query(
        self,
        request: RAGQueryRequest,
        storage_repository  # 传入storage_repository
    ) -> RAGQueryResponse:
        """RAG问答"""
        try:
            start_time = time.time()

            # 通过MCP进行RAG查询
            rag_result = await self._rag_query_via_mcp(
                user_id=request.user_id,
                query=request.query,
                rag_mode=request.rag_mode.value,
                top_k=request.top_k,
                max_tokens=request.max_tokens,
                temperature=request.temperature
            )

            # 构建sources列表
            sources = []
            for source in rag_result.get("sources", []):
                file_id = source.get("metadata", {}).get("file_id", "")
                doc_id = source.get("metadata", {}).get("doc_id", "")

                file_record = await storage_repository.get_file_by_id(file_id, request.user_id)
                if file_record:
                    sources.append(SearchResult(
                        file_id=file_id,
                        doc_id=doc_id,
                        file_name=file_record.file_name,
                        relevance_score=source.get("relevance_score", 0.0),
                        content_snippet=source.get("text", "")[:200],
                        file_type=file_record.content_type,
                        file_size=file_record.file_size,
                        metadata=file_record.metadata,
                        uploaded_at=file_record.uploaded_at,
                        download_url=file_record.download_url
                    ))

            # 提取引用 (转换为字符串列表)
            citations = None
            if request.enable_citations:
                citation_objs = rag_result.get("citations", [])
                if citation_objs:
                    citations = [
                        c.get("text", "") if isinstance(c, dict) else str(c)
                        for c in citation_objs
                    ]

            rag_answer = RAGAnswer(
                answer=rag_result.get("response", ""),
                confidence=rag_result.get("confidence", 0.8),
                sources=sources,
                citations=citations,
                session_id=request.session_id
            )

            latency_ms = (time.time() - start_time) * 1000

            return RAGQueryResponse(
                query=request.query,
                rag_answer=rag_answer,
                latency_ms=latency_ms
            )

        except Exception as e:
            logger.error(f"Error in RAG query: {e}")
            raise

    async def _rag_query_via_mcp(
        self,
        user_id: str,
        query: str,
        rag_mode: str,
        top_k: int,
        max_tokens: int,
        temperature: float
    ) -> Dict[str, Any]:
        """通过MCP调用generate_rag_response (JSON-RPC 2.0 format)"""
        try:
            async with httpx.AsyncClient(timeout=90.0) as client:
                # Use JSON-RPC 2.0 format per how_to_mcp.md
                # Stream the response to handle SSE properly
                async with client.stream(
                    "POST",
                    f"{self.mcp_endpoint}/mcp",
                    headers={
                        'Content-Type': 'application/json',
                        'Accept': 'application/json, text/event-stream'
                    },
                    json={
                        "jsonrpc": "2.0",
                        "id": 3,
                        "method": "tools/call",
                        "params": {
                            "name": "generate_rag_response",
                            "arguments": {
                                "user_id": user_id,
                                "query": query,
                                "context_limit": top_k
                                # Note: mode/temperature not in basic generate_rag_response
                                # Use query_with_mode for specific RAG modes
                            }
                        }
                    }
                ) as response:
                    if response.status_code == 200:
                        # Read the SSE stream
                        response_text = ""
                        async for chunk in response.aiter_text():
                            response_text += chunk
                        
                        # Parse SSE response
                        result = self._parse_sse_response(response_text)
                        if result and 'result' in result:
                            content = result['result'].get('content', [])
                            if content:
                                data = json.loads(content[0].get('text', '{}'))
                                # Based on how_to_digital.md line 329-352
                                return data.get('data', {})
                        return {
                            "response": "Failed to parse MCP response",
                            "sources": [],
                            "confidence": 0.0
                        }
                    else:
                        logger.error(f"MCP RAG failed: {response.status_code}")
                        return {
                            "response": "Failed to generate response",
                            "sources": [],
                            "confidence": 0.0
                        }

        except Exception as e:
            logger.error(f"Error calling MCP generate_rag_response: {e}")
            return {
                "response": "Error generating response",
                "sources": [],
                "confidence": 0.0
            }

    # ==================== 统计 ====================

    async def get_stats(
        self,
        user_id: str,
        storage_repository
    ) -> IntelligenceStats:
        """获取智能统计"""
        try:
            # 获取智能索引统计
            intel_stats = await self.repository.get_user_stats(user_id)

            # 获取存储统计
            storage_stats = await storage_repository.get_storage_stats(user_id=user_id)

            return IntelligenceStats(
                user_id=user_id,
                total_files=storage_stats.get("file_count", 0),
                indexed_files=intel_stats["indexed_files"],
                total_chunks=intel_stats["total_chunks"],
                total_searches=intel_stats["total_searches"],
                avg_search_latency_ms=0.0,  # TODO: Track in search_history
                storage_size_bytes=storage_stats.get("total_size", 0)
            )

        except Exception as e:
            logger.error(f"Error getting stats: {e}")
            raise

    # ==================== 图片智能处理 ====================

    async def _store_image_via_mcp(
        self,
        user_id: str,
        image_path: str,
        metadata: Optional[Dict[str, Any]] = None,
        description_prompt: Optional[str] = None,
        model: str = "gpt-4o-mini"
    ) -> Dict[str, Any]:
        """
        通过MCP调用store_knowledge存储图片

        使用新的统一工具: store_knowledge
        content_type="image" 会自动触发VLM分析

        Returns:
            {
                "success": True,
                "chunks_stored": 1,
                "ai_metadata": {
                    "ai_categories": ["landscape"],
                    "ai_tags": ["mountains", "sunset"],
                    "ai_mood": "peaceful",
                    "ai_dominant_colors": ["blue", "orange"],
                    "ai_quality_score": 0.9,
                    ...
                },
                "operation_id": "uuid"
            }
        """
        try:
            # 准备元数据
            store_metadata = metadata or {}
            if description_prompt:
                store_metadata["description_prompt"] = description_prompt
            if model:
                store_metadata["model"] = model

            logger.info(f"Storing image via MCP: user={user_id}, path={image_path[:50]}...")

            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(
                    f"{self.mcp_endpoint}/mcp",
                    headers={
                        'Content-Type': 'application/json',
                        'Accept': 'application/json, text/event-stream'
                    },
                    json={
                        "jsonrpc": "2.0",
                        "id": 1,
                        "method": "tools/call",
                        "params": {
                            "name": "store_knowledge",
                            "arguments": {
                                "user_id": user_id,
                                "content": image_path,
                                "content_type": "image",
                                "metadata": store_metadata
                            }
                        }
                    }
                )

                if response.status_code == 200:
                    logger.info(f"MCP store_knowledge response: {response.text[:1000]}")
                    result = self._parse_sse_response(response.text)

                    if result and 'data' in result:
                        data = result['data']
                        logger.info(f"Parsed data keys: {list(data.keys())}")
                        logger.info(f"Full metadata structure: {json.dumps(data.get('metadata', {}), indent=2)[:500]}")

                        if not data.get('success'):
                            error_msg = data.get('error', 'Unknown error')
                            logger.error(f"store_knowledge failed: {error_msg}")
                            raise Exception(f"store_knowledge failed: {error_msg}")

                        # 提取AI元数据
                        metadata_info = data.get('metadata', {})
                        # AI metadata is nested under ai_metadata key
                        ai_metadata = metadata_info.get('ai_metadata', {})
                        chunks_stored = metadata_info.get('chunks_processed', 0)
                        operation_id = data.get('operation_id', 'unknown')

                        logger.info(f"✅ Image stored: {chunks_stored} chunks, operation_id={operation_id}")
                        logger.info(f"metadata_info keys: {list(metadata_info.keys())}")
                        logger.info(f"AI metadata keys: {list(ai_metadata.keys())}")
                        if ai_metadata:
                            logger.info(f"AI categories: {ai_metadata.get('ai_categories')}")
                            logger.info(f"AI tags: {ai_metadata.get('ai_tags', [])[:5]}")

                        # 从 chunks 中提取描述文本（如果有的话）
                        description_text = ""
                        if chunks_stored > 0:
                            # 描述文本通常存储在第一个 chunk 的 text 中
                            description_text = f"AI-generated description (len={metadata_info.get('text_length', 0)})"

                        return {
                            "success": True,
                            "description": description_text,  # VLM描述文本
                            "description_length": metadata_info.get('text_length', 0),
                            "metadata": ai_metadata,
                            "operation_id": operation_id,
                            "chunks_stored": chunks_stored,
                            # 兼容旧格式
                            "vlm_model": store_metadata.get("model", "gpt-4o-mini"),
                            "storage_id": operation_id
                        }

                    logger.error(f"MCP store_knowledge parse failed. Result: {result}")
                    raise Exception(f"Failed to parse MCP response")

                logger.error(f"MCP store_knowledge failed: {response.status_code} - {response.text}")
                raise Exception(f"MCP store_knowledge failed: {response.status_code}")

        except Exception as e:
            logger.error(f"Error calling MCP store_knowledge: {e}")
            raise

    async def _search_images_via_mcp(
        self,
        user_id: str,
        query: str,
        top_k: int = 5,
        enable_rerank: bool = False,
        search_mode: str = "semantic"
    ) -> Dict[str, Any]:
        """
        通过MCP调用search_knowledge搜索图片

        使用新的统一工具: search_knowledge
        指定 content_types=["image"] 来只搜索图片

        Returns:
            {
                "success": True,
                "total_results": 3,
                "results": [
                    {
                        "text": "VLM描述...",
                        "score": 0.92,
                        "metadata": {
                            "file_id": "...",
                            "ai_categories": [...],
                            "ai_tags": [...],
                            ...
                        }
                    }
                ]
            }
        """
        try:
            logger.info(f"Searching images via MCP: user={user_id}, query='{query}', top_k={top_k}")

            # 准备搜索选项
            search_options = {
                "top_k": top_k,
                "content_types": ["image"]  # 只搜索图片
            }

            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    f"{self.mcp_endpoint}/mcp",
                    headers={
                        'Content-Type': 'application/json',
                        'Accept': 'application/json, text/event-stream'
                    },
                    json={
                        "jsonrpc": "2.0",
                        "id": 1,
                        "method": "tools/call",
                        "params": {
                            "name": "search_knowledge",
                            "arguments": {
                                "user_id": user_id,
                                "query": query,
                                "search_options": search_options
                            }
                        }
                    }
                )

                if response.status_code == 200:
                    result = self._parse_sse_response(response.text)

                    if result and 'data' in result:
                        data = result['data']

                        if not data.get('success'):
                            error_msg = data.get('error', 'Unknown error')
                            logger.error(f"search_knowledge failed: {error_msg}")
                            return {
                                "success": False,
                                "error": error_msg,
                                "image_results": []
                            }

                        total_results = data.get('total_results', 0)
                        results = data.get('results', [])

                        logger.info(f"✅ Found {total_results} images")

                        # 转换为旧格式（兼容性）
                        image_results = []
                        for item in results:
                            metadata = item.get('metadata', {})
                            image_results.append({
                                "knowledge_id": metadata.get('chunk_id', ''),
                                "image_path": metadata.get('image_path', ''),
                                "description": item.get('text', ''),
                                "relevance_score": item.get('score', 0.0),
                                "metadata": metadata,
                                "search_method": "semantic_vector"
                            })

                        return {
                            "success": True,
                            "total_images_found": total_results,
                            "image_results": image_results,
                            "search_method": "search_knowledge"
                        }

                    logger.error(f"MCP search_knowledge parse failed. Result: {result}")
                    raise Exception(f"Failed to parse MCP response")

                logger.error(f"MCP search_knowledge failed: {response.status_code}")
                raise Exception(f"MCP search_knowledge failed: {response.status_code}")

        except Exception as e:
            logger.error(f"Error calling MCP search_knowledge: {e}")
            raise

    async def _generate_image_rag_via_mcp(
        self,
        user_id: str,
        query: str,
        context_limit: int = 3,
        include_images: bool = True,
        rag_mode: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        通过MCP调用knowledge_response生成RAG响应

        使用新的统一工具: knowledge_response
        自动检索相关内容并生成回答

        Returns:
            {
                "success": True,
                "response": "回答内容...",
                "sources": [
                    {
                        "text": "来源内容",
                        "score": 0.92,
                        "metadata": {...}
                    }
                ],
                "citations": [...]
            }
        """
        try:
            logger.info(f"Generating RAG response: user={user_id}, query='{query}'")

            # 准备响应选项
            response_options = {
                "rag_mode": rag_mode or "simple",
                "context_limit": context_limit,
                "enable_citations": True
            }

            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(
                    f"{self.mcp_endpoint}/mcp",
                    headers={
                        'Content-Type': 'application/json',
                        'Accept': 'application/json, text/event-stream'
                    },
                    json={
                        "jsonrpc": "2.0",
                        "id": 1,
                        "method": "tools/call",
                        "params": {
                            "name": "knowledge_response",
                            "arguments": {
                                "user_id": user_id,
                                "query": query,
                                "response_options": response_options
                            }
                        }
                    }
                )

                if response.status_code == 200:
                    logger.debug(f"MCP knowledge_response response: {response.text[:500]}")
                    result = self._parse_sse_response(response.text)

                    if result and 'data' in result:
                        data = result['data']

                        if not data.get('success'):
                            error_msg = data.get('error', 'Unknown error')
                            logger.error(f"knowledge_response failed: {error_msg}")
                            return {
                                "success": False,
                                "error": error_msg,
                                "response": ""
                            }

                        response_text = data.get('response', '')
                        sources = data.get('sources', [])
                        citations = data.get('citations', [])

                        logger.info(f"✅ Generated RAG response ({len(response_text)} chars, {len(sources)} sources)")

                        return {
                            "success": True,
                            "response": response_text,
                            "answer": response_text,  # 兼容旧格式
                            "sources": sources,
                            "context": sources,  # 兼容旧格式
                            "citations": citations,
                            "total_sources": len(sources)
                        }

                    logger.error(f"MCP knowledge_response parse failed. Result: {result}")
                    raise Exception(f"Failed to parse MCP response")

                logger.error(f"MCP knowledge_response failed: {response.status_code} - {response.text}")
                raise Exception(f"MCP knowledge_response failed: {response.status_code}")

        except Exception as e:
            logger.error(f"Error calling MCP knowledge_response: {e}")
            raise
