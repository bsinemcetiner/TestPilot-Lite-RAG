from pydantic import BaseModel, ConfigDict
from typing import List, Dict, Any, Optional
from datetime import datetime
from app.schemas.test_case import TestCaseSchema


class GenerationRunBase(BaseModel):
    feature: str
    query: Optional[str]
    provider: str
    output_format: str
    requested_count: int
    retrieved_chunks_count: int
    is_pinned: bool
    evaluation_metrics: Optional[Dict[str, Any]] = None
    formatted_output: Optional[str] = None


class GenerationRunResponse(GenerationRunBase):
    id: str
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class GeneratedTestCaseResponse(BaseModel):
    id: int
    run_id: str
    case_index: int
    title: str
    type: str
    priority: str
    expected_result: str
    confidence: Optional[float]
    preconditions: List[str]
    steps: List[str]
    source_references: Optional[List[Dict[str, Any]]]

    model_config = ConfigDict(from_attributes=True)


class GenerationRunDetailResponse(GenerationRunResponse):
    test_cases: List[GeneratedTestCaseResponse]
    
    model_config = ConfigDict(from_attributes=True)
