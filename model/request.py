from pydantic import BaseModel
from typing import List, Optional, Any
from enum import Enum

class TaskStatus(str, Enum):
    PENDING = "PENDING"
    EXTRACTING = "EXTRACTING"
    EXTRACT_SUCCESS = "EXTRACT_SUCCESS"
    GENERATING = "GENERATING"
    GENERATE_SUCCESS = "GENERATE_SUCCESS"
    FAILED = "FAILED"

class InitialRequest(BaseModel):
    """
    공적조서 최초 추출 요청 (Phase 1)
    """
    hr_id: str
    hr_pw: str
    prompt: str

class GenerationRequest(BaseModel):
    """
    공적조서 최종 생성 요청 (Phase 2)
    """
    task_id: str
    selected_contexts: List[str]  # 이전 단계 결과 중 선택된 내용들
    prompt: str
