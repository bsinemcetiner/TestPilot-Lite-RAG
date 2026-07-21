from pydantic import BaseModel, Field
from typing import List, Optional, Literal


class SourceReference(BaseModel):
    document_name: str
    chunk_id: str
    quote: Optional[str] = None


class TestCaseSchema(BaseModel):
    id: int
    title: str
    type: Literal['Positive', 'Negative', 'Edge Case', 'Validation', 'Security']
    priority: Literal['High', 'Medium', 'Low']
    preconditions: List[str]
    steps: List[str]
    expected_result: str
    source_references: List[SourceReference] = Field(default_factory=list)
    confidence: Optional[float] = None
