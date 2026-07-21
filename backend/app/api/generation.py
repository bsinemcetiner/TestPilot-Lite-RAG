import json
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.services.rag_service import RAGService
from app.services.generation_service import TestCaseGenerator
from app.services.evaluation_service import EvaluationService
from app.schemas.generation import GenerationRequestSchema, GenerationResponseSchema
from typing import List


router = APIRouter()

class SearchRequest(BaseModel):
    query: str
    n_results: int = 5


# Use shared schema for request validation and documentation.


class GenerationRequest(GenerationRequestSchema):
    pass


@router.post("/search")
def search_documents(request: SearchRequest):
    """
    Search for relevant document chunks based on query.
    """
    try:
        results = RAGService.retrieve_context(request.query, n_results=request.n_results)
        return {"results": results, "count": len(results)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


@router.post("/generate-tests", response_model=GenerationResponseSchema)
def generate_test_cases(request: GenerationRequest):
    """
    Generate test cases based on feature name and relevant documents.
    Supports multiple output formats and includes quality evaluation.
    """
    try:
        retrieved = RAGService.retrieve_context(request.query, n_results=5)
        
        if not retrieved:
            raise HTTPException(
                status_code=404,
                detail="No relevant documents found for the query."
            )
        
        test_cases, used_provider = TestCaseGenerator.generate_test_cases(
            feature_name=request.feature_name,
            query=request.query,
            retrieved_context=retrieved,
            test_types=request.test_types,
            num_cases=request.num_cases,
            provider_name=request.provider,
        )

        requirements: List[str] = []

        for chunk in retrieved:
            chunk_text = str(
                chunk.get("text")
                or chunk.get("content")
                or chunk.get("document")
                or chunk.get("page_content")
                or ""
            ).strip()

            if not chunk_text:
                continue

            try:
                parsed_chunk = json.loads(chunk_text)

                chunk_requirements = parsed_chunk.get(
                    "requirements",
                    [],
                )

                if isinstance(chunk_requirements, list):
                    requirements.extend(
                        str(requirement).strip()
                        for requirement in chunk_requirements
                        if str(requirement).strip()
                    )

            except (json.JSONDecodeError, TypeError):
                continue

        requirements = list(dict.fromkeys(requirements))

        evaluation = EvaluationService.evaluate_test_cases(
            test_cases=test_cases,
            requirements=requirements,
        )
        
        output = {
            "test_cases": test_cases,
            "count": len(test_cases),
            "feature": request.feature_name,
            "retrieved_chunks": len(retrieved),
            "provider": used_provider,
            "evaluation": evaluation,
        }
        
        if request.output_format == "markdown":
            output["formatted"] = TestCaseGenerator.to_markdown(test_cases)
        elif request.output_format == "csv":
            output["formatted"] = TestCaseGenerator.to_csv(test_cases)
        elif request.output_format == "gherkin":
            gherkin_output = "\n".join([
                TestCaseGenerator.to_gherkin(tc) for tc in test_cases
            ])
            output["formatted"] = gherkin_output
        else:
            output["formatted"] = TestCaseGenerator.to_json(test_cases)
        
        return output

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Generation failed: {str(e)}",
        )
