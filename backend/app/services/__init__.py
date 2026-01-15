"""
服务模块
提供 OCR、合同提取等业务服务
"""

from app.services.ocr import (
    pdf_to_images,
    pdf_bytes_to_images,
    ocr_images,
    extract_text_from_pdf,
    filter_watermarks,
)
from app.services.extractor import (
    extract_contract_info,
    extract_with_vision,
    extract_with_text,
    images_to_blob,
)

from app.services.vector_search import (
    get_embedding,
    get_embeddings_batch,
    search_performances_by_vector,
    hybrid_search_performances,
    search_lawyers_by_resume,
    update_performance_embedding,
    batch_update_embeddings,
)

__all__ = [
    # OCR
    "pdf_to_images",
    "pdf_bytes_to_images",
    "ocr_images",
    "extract_text_from_pdf",
    "filter_watermarks",
    # 提取
    "extract_contract_info",
    "extract_with_vision",
    "extract_with_text",
    "images_to_blob",
    # 向量搜索
    "get_embedding",
    "get_embeddings_batch",
    "search_performances_by_vector",
    "hybrid_search_performances",
    "search_lawyers_by_resume",
    "update_performance_embedding",
    "batch_update_embeddings",
]