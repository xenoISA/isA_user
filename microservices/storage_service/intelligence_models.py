"""
Storage Service - Intelligence Models

智能文档分析相关的数据模型 (集成到storage_service)
"""

from datetime import datetime
from typing import Optional, Dict, Any, List
from enum import Enum
from pydantic import BaseModel, Field, ConfigDict


# ==================== Enums ====================

class DocumentStatus(str, Enum):
    """文档索引状态"""
    PENDING = "pending"
    PROCESSING = "processing"
    INDEXED = "indexed"
    FAILED = "failed"
    DELETED = "deleted"


class RAGMode(str, Enum):
    """RAG处理模式"""
    SIMPLE = "simple"
    RAPTOR = "raptor"
    SELF_RAG = "self_rag"
    CRAG = "crag"
    PLAN_RAG = "plan_rag"
    HM_RAG = "hm_rag"


class ChunkingStrategy(str, Enum):
    """文档分块策略"""
    FIXED = "fixed"
    SEMANTIC = "semantic"
    SLIDING_WINDOW = "sliding_window"
    RECURSIVE = "recursive"


# ==================== Database Models ====================

class IndexedDocument(BaseModel):
    """索引文档模型"""
    model_config = ConfigDict(from_attributes=True)

    id: Optional[int] = None
    doc_id: str = Field(..., description="文档唯一标识")
    file_id: str = Field(..., description="关联的存储文件ID")
    user_id: str = Field(..., description="用户ID")
    organization_id: Optional[str] = Field(None, description="组织ID")

    title: str = Field(..., description="文档标题")
    content_preview: Optional[str] = Field(None, description="内容预览")

    status: DocumentStatus = Field(DocumentStatus.PENDING, description="索引状态")
    chunking_strategy: ChunkingStrategy = Field(ChunkingStrategy.SEMANTIC, description="分块策略")
    chunk_count: int = Field(0, description="分块数量")

    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="元数据")
    tags: Optional[List[str]] = Field(default_factory=list, description="标签")

    search_count: int = Field(0, description="搜索次数")
    last_accessed_at: Optional[datetime] = Field(None, description="最后访问时间")

    indexed_at: Optional[datetime] = Field(None, description="索引时间")
    updated_at: Optional[datetime] = Field(None, description="更新时间")


# ==================== Request/Response Models ====================

class IntelligentUploadRequest(BaseModel):
    """智能上传请求 - 上传文件并自动索引"""
    user_id: str
    organization_id: Optional[str] = None

    # 文件存储参数
    access_level: str = "private"

    # 智能索引参数
    auto_index: bool = Field(True, description="自动建立智能索引")
    chunking_strategy: ChunkingStrategy = Field(ChunkingStrategy.SEMANTIC, description="分块策略")
    chunk_size: int = Field(512, ge=128, le=2048, description="分块大小")

    metadata: Optional[Dict[str, Any]] = None
    tags: Optional[List[str]] = None


class SearchResult(BaseModel):
    """搜索结果"""
    file_id: str
    doc_id: Optional[str] = None
    file_name: str
    relevance_score: float
    content_snippet: str
    file_type: str
    file_size: int
    metadata: Dict[str, Any]
    uploaded_at: datetime
    download_url: Optional[str] = None


class SemanticSearchRequest(BaseModel):
    """语义搜索请求"""
    user_id: str
    query: str = Field(..., min_length=1, description="搜索查询")

    top_k: int = Field(5, ge=1, le=50, description="返回结果数量")
    enable_rerank: bool = Field(False, description="启用重排序")
    min_score: float = Field(0.0, ge=0.0, le=1.0, description="最低相关性分数")

    file_types: Optional[List[str]] = Field(None, description="文件类型过滤")
    tags: Optional[List[str]] = Field(None, description="标签过滤")


class SemanticSearchResponse(BaseModel):
    """语义搜索响应"""
    query: str
    results: List[SearchResult]
    results_count: int
    latency_ms: float
    message: str = "Search completed successfully"


class RAGQueryRequest(BaseModel):
    """RAG问答请求"""
    user_id: str
    query: str = Field(..., min_length=1, description="用户问题")

    rag_mode: RAGMode = Field(RAGMode.SIMPLE, description="RAG模式")
    session_id: Optional[str] = Field(None, description="会话ID(多轮对话)")

    top_k: int = Field(3, ge=1, le=10, description="检索文档数量")
    enable_citations: bool = Field(True, description="启用引用")

    max_tokens: int = Field(500, ge=50, le=2000, description="最大生成长度")
    temperature: float = Field(0.7, ge=0.0, le=1.0, description="生成温度")


class RAGAnswer(BaseModel):
    """RAG回答"""
    answer: str
    confidence: float
    sources: List[SearchResult]
    citations: Optional[List[str]] = None
    session_id: Optional[str] = None


class RAGQueryResponse(BaseModel):
    """RAG问答响应"""
    query: str
    rag_answer: RAGAnswer
    latency_ms: float
    message: str = "Query completed successfully"


class IntelligenceStats(BaseModel):
    """智能统计"""
    user_id: str
    total_files: int
    indexed_files: int
    total_chunks: int
    total_searches: int
    avg_search_latency_ms: float
    storage_size_bytes: int


# ==================== 图片智能处理 ====================

class StoreImageRequest(BaseModel):
    """存储图片请求"""
    user_id: str
    image_path: str = Field(..., description="本地图片路径")
    metadata: Optional[Dict[str, Any]] = Field(None, description="自定义元数据")
    description_prompt: Optional[str] = Field(None, description="自定义VLM提示词")
    model: str = Field("gpt-4o-mini", description="VLM模型")


class StoreImageResponse(BaseModel):
    """存储图片响应"""
    success: bool
    image_path: str
    description: str
    description_length: int
    storage_id: str
    vlm_model: str
    processing_time: float
    metadata: Dict[str, Any]
    message: str = "Image stored successfully"


class ImageSearchRequest(BaseModel):
    """图片搜索请求"""
    user_id: str
    query: str = Field(..., min_length=1, description="搜索查询")
    top_k: int = Field(5, ge=1, le=50, description="返回结果数量")
    enable_rerank: bool = Field(False, description="启用重排序")
    search_mode: str = Field("semantic", description="搜索模式")


class ImageSearchResult(BaseModel):
    """图片搜索结果"""
    knowledge_id: str
    image_path: str
    description: str
    relevance_score: float
    metadata: Dict[str, Any]
    search_method: str


class ImageSearchResponse(BaseModel):
    """图片搜索响应"""
    success: bool
    user_id: str
    query: str
    image_results: List[ImageSearchResult]
    total_images_found: int
    search_method: str
    message: str = "Image search completed successfully"


class ImageRAGRequest(BaseModel):
    """图片RAG请求"""
    user_id: str
    query: str = Field(..., min_length=1, description="用户问题")
    context_limit: int = Field(3, ge=1, le=10, description="上下文数量")
    include_images: bool = Field(True, description="包含图片")
    rag_mode: Optional[str] = Field(None, description="RAG模式")


class ImageSource(BaseModel):
    """图片来源"""
    image_path: str
    description: str
    relevance: float


class ImageRAGResponse(BaseModel):
    """图片RAG响应"""
    success: bool
    response: str
    context_items: int
    image_sources: List[ImageSource]
    text_sources: List[SearchResult]
    metadata: Dict[str, Any]
    message: str = "Image RAG completed successfully"
