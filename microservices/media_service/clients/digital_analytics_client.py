"""
Media Service - Digital Analytics Service Client

封装对 Digital Analytics Service (isA_Data) 的 HTTP 调用
提供 RAG、PDF 处理、图像处理等能力
"""

import logging
from typing import Any, AsyncIterator, Dict, List, Optional

import httpx
from core.config_manager import ConfigManager

logger = logging.getLogger(__name__)


class DigitalAnalyticsClient:
    """
    Digital Analytics Service 客户端

    提供以下功能:
    - 多模态内容存储 (文本、PDF、图像)
    - 7种 RAG 模式检索
    - AI 驱动的内容分析和回答生成
    """

    def __init__(self, base_url: Optional[str] = None):
        """
        初始化客户端

        Args:
            base_url: Digital Analytics Service 的基础 URL
                     如果为 None，则从配置中读取
        """
        if base_url is None:
            config = ConfigManager("media_service")
            service_config = config.get_service_config()
            self.base_url = service_config.digital_analytics_url
            self.enabled = service_config.digital_analytics_enabled
        else:
            self.base_url = base_url
            self.enabled = True

        if not self.base_url:
            logger.warning("Digital Analytics Service URL not configured")
            self.enabled = False
        elif not self.base_url.endswith("/api/v1/digital"):
            self.base_url = f"{self.base_url.rstrip('/')}/api/v1/digital"

        self.client = httpx.AsyncClient(timeout=300.0)  # 5 minutes for AI processing

    async def close(self):
        """关闭 HTTP 客户端"""
        await self.client.aclose()

    async def __aenter__(self):
        """Context manager 入口"""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager 退出"""
        await self.close()

    def is_enabled(self) -> bool:
        """检查服务是否启用"""
        return self.enabled and bool(self.base_url)

    async def store_content(
        self,
        user_id: str,
        content: str,
        content_type: str = "text",  # text, pdf, image
        mode: str = "simple",  # RAG mode
        collection_name: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        存储内容到知识库

        Args:
            user_id: 用户ID
            content: 内容（文本或 URL）
            content_type: 内容类型 (text, pdf, image)
            mode: RAG 模式
            collection_name: 集合名称
            metadata: 元数据

        Returns:
            存储结果

        Example:
            # 存储 PDF
            result = await client.store_content(
                user_id="alice",
                content="https://example.com/doc.pdf",
                content_type="pdf",
                collection_name="user_documents"
            )
        """
        if not self.is_enabled():
            logger.warning("Digital Analytics Service is not enabled")
            return None

        try:
            payload = {
                "user_id": user_id,
                "content": content,
                "content_type": content_type,
                "mode": mode,
            }

            if collection_name:
                payload["collection_name"] = collection_name
            if metadata:
                payload["metadata"] = metadata

            response = await self.client.post(
                f"{self.base_url}/store",
                json=payload,
            )
            response.raise_for_status()

            # Store endpoint returns SSE stream, we need to consume it
            result = None
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    import json

                    try:
                        data = json.loads(line[6:])
                        if data.get("type") == "result":
                            result = data.get("data")
                            logger.info(
                                f"🔍 SSE result received: ai_metadata keys = {list(result.get('ai_metadata', {}).keys()) if result else 'None'}"
                            )
                    except json.JSONDecodeError:
                        pass

            # The result.data contains ai_metadata at top level
            # Example: {"success": true, "ai_metadata": {...}, "metadata": {...}}
            logger.info(f"🔍 Final result: {result.keys() if result else 'None'}")
            if result and "ai_metadata" in result:
                logger.info(f"🔍 Final ai_metadata: {result['ai_metadata']}")
            return result

        except Exception as e:
            logger.error(
                f"Failed to store content via Digital Analytics Service: {e}",
                exc_info=True,
            )
            return None

    async def search_content(
        self,
        user_id: str,
        query: str,
        mode: str = "simple",
        collection_name: Optional[str] = None,
        top_k: int = 5,
        options: Optional[Dict[str, Any]] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        搜索内容

        Args:
            user_id: 用户ID
            query: 查询文本
            mode: RAG 模式
            collection_name: 集合名称
            top_k: 返回结果数量
            options: 模式特定选项

        Returns:
            搜索结果

        Example:
            result = await client.search_content(
                user_id="alice",
                query="What is in this document?",
                mode="rag_fusion",
                collection_name="user_documents",
                top_k=3
            )
        """
        if not self.is_enabled():
            logger.warning("Digital Analytics Service is not enabled")
            return None

        try:
            payload = {
                "user_id": user_id,
                "query": query,
                "mode": mode,
                "top_k": top_k,
            }

            if collection_name:
                payload["collection_name"] = collection_name
            if options:
                payload["options"] = options

            response = await self.client.post(
                f"{self.base_url}/search",
                json=payload,
            )
            response.raise_for_status()

            # Search endpoint returns SSE stream
            result = None
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    import json

                    try:
                        data = json.loads(line[6:])
                        if data.get("type") == "result":
                            result = data.get("data")
                    except json.JSONDecodeError:
                        pass

            return result

        except Exception as e:
            logger.error(
                f"Failed to search content via Digital Analytics Service: {e}",
                exc_info=True,
            )
            return None

    async def generate_response(
        self,
        user_id: str,
        query: str,
        mode: str = "simple",
        collection_name: Optional[str] = None,
        top_k: int = 5,
        options: Optional[Dict[str, Any]] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        生成 AI 回答

        Args:
            user_id: 用户ID
            query: 查询文本
            mode: RAG 模式
            collection_name: 集合名称
            top_k: 检索结果数量
            options: 模式特定选项 (如 use_citations)

        Returns:
            生成的回答

        Example:
            result = await client.generate_response(
                user_id="alice",
                query="Summarize this document",
                mode="simple",
                collection_name="user_documents",
                options={"use_citations": True}
            )
        """
        if not self.is_enabled():
            logger.warning("Digital Analytics Service is not enabled")
            return None

        try:
            payload = {
                "user_id": user_id,
                "query": query,
                "mode": mode,
                "top_k": top_k,
            }

            if collection_name:
                payload["collection_name"] = collection_name
            if options:
                payload["options"] = options

            response = await self.client.post(
                f"{self.base_url}/response",
                json=payload,
            )
            response.raise_for_status()

            # Response endpoint returns SSE stream
            result = None
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    import json

                    try:
                        data = json.loads(line[6:])
                        if data.get("type") == "result":
                            result = data.get("data")
                    except json.JSONDecodeError:
                        pass

            return result

        except Exception as e:
            logger.error(
                f"Failed to generate response via Digital Analytics Service: {e}",
                exc_info=True,
            )
            return None

    # Convenience methods for common use cases

    async def process_pdf(
        self,
        user_id: str,
        pdf_url: str,
        collection_name: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        处理 PDF 文档

        Args:
            user_id: 用户ID
            pdf_url: PDF 文件 URL
            collection_name: 集合名称
            metadata: 元数据

        Returns:
            处理结果
        """
        return await self.store_content(
            user_id=user_id,
            content=pdf_url,
            content_type="pdf",
            mode="simple",
            collection_name=collection_name,
            metadata=metadata,
        )

    async def process_image(
        self,
        user_id: str,
        image_url: str,
        collection_name: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        处理图像

        Args:
            user_id: 用户ID
            image_url: 图像 URL
            collection_name: 集合名称
            metadata: 元数据

        Returns:
            处理结果（包含图像描述和向量化）
        """
        return await self.store_content(
            user_id=user_id,
            content=image_url,
            content_type="image",
            mode="simple",
            collection_name=collection_name,
            metadata=metadata,
        )

    async def extract_pdf_info(
        self,
        user_id: str,
        pdf_url: str,
        query: str = "What is this document about?",
    ) -> Optional[str]:
        """
        提取 PDF 信息

        Args:
            user_id: 用户ID
            pdf_url: PDF URL
            query: 查询问题

        Returns:
            提取的信息文本
        """
        # First store the PDF
        collection = f"temp_pdf_{user_id}"
        store_result = await self.process_pdf(
            user_id=user_id,
            pdf_url=pdf_url,
            collection_name=collection,
        )

        if not store_result or not store_result.get("success"):
            return None

        # Then query it
        response = await self.generate_response(
            user_id=user_id,
            query=query,
            collection_name=collection,
        )

        if response and response.get("success"):
            return response.get("response")

        return None

    async def describe_image(
        self,
        user_id: str,
        image_url: str,
        query: str = "Describe this image in detail",
    ) -> Optional[str]:
        """
        描述图像内容

        Args:
            user_id: 用户ID
            image_url: 图像 URL
            query: 查询问题

        Returns:
            图像描述文本
        """
        # First store the image
        collection = f"temp_image_{user_id}"
        store_result = await self.process_image(
            user_id=user_id,
            image_url=image_url,
            collection_name=collection,
        )

        if not store_result or not store_result.get("success"):
            return None

        # Then query it
        response = await self.generate_response(
            user_id=user_id,
            query=query,
            collection_name=collection,
        )

        if response and response.get("success"):
            return response.get("response")

        return None
