from typing import List, Literal

from pydantic import BaseModel, Field

from app.schemas.test_case import TestCaseSchema


class GenerationRequestSchema(BaseModel):
    feature_name: str = Field(
        min_length=2,
        max_length=150,
    )

    query: str = Field(
        min_length=5,
        max_length=3000,
    )

    test_types: List[str] = Field(
        default_factory=lambda: [
            "Positive",
            "Negative",
            "Edge Case",
        ]
    )

    num_cases: int = Field(
        default=5,
        ge=1,
        le=20,
    )

    output_format: Literal[
        "json",
        "markdown",
        "csv",
        "gherkin",
    ] = "json"

    provider: str = "mock"


class GenerationResponseSchema(BaseModel):
    test_cases: List[TestCaseSchema]
    count: int
    feature: str
    retrieved_chunks: int
    provider: str
    formatted: str
    evaluation: dict