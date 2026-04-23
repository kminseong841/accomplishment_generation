from pydantic import BaseModel, Field
from typing import List, Optional

# --- 기초 문서 모델 (Basic Document Models) ---

class HrDocument(BaseModel):
    """인사 정보 데이터 모델"""
    pass

class AssessmentDocument(BaseModel):
    """평가 정보 데이터 모델"""
    pass

class OnnaraDocument(BaseModel):
    """온나라 시스템 추출 문서 모델"""
    pass

# --- 2-Phase 데이터 분류 모델 ---

class ExtractedData(BaseModel):
    """
    Phase 1: 시스템별 추출 데이터 계층
    (CS 제안 반영: data_extracted -> extracted_data, assessment -> assessments)
    """
    hr: Optional[HrDocument] = None
    assessments: List[AssessmentDocument] = Field(default_factory=list)
    onnara: List[OnnaraDocument] = Field(default_factory=list)

class GeneratedData(BaseModel):
    """
    Phase 2: LLM 생성 데이터 계층
    (사용자 요청: summary, accomplishment 명칭 유지)
    """
    summary: Optional[str] = None
    accomplishment: Optional[str] = None

class TaskPayload(BaseModel):
    """
    태스크의 실제 데이터 알맹이 (기존의 'content' 내부 구조)
    """
    extracted_data: Optional[ExtractedData] = None
    generated_data: Optional[GeneratedData] = None

# --- 최상위 DB 저장 레코드 모델 ---

class TaskRecord(BaseModel):
    """
    DB에 저장되는 최종 태스크 정보
    """
    task_id: str
    status: str
    content: Optional[TaskPayload] = None
    message: Optional[str] = None
