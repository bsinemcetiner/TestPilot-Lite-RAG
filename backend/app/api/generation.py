import json
import re
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.services.rag_service import RAGService
from app.services.generation_service import TestCaseGenerator
from app.services.evaluation_service import EvaluationService
from app.schemas.generation import GenerationRequestSchema, GenerationResponseSchema
from typing import List
import uuid
from sqlalchemy.orm import Session
from fastapi import Depends

from app.db.database import SessionLocal
from app.db.models import GenerationRun, GeneratedTestCase
from app.schemas.history import GenerationRunResponse, GenerationRunDetailResponse


router = APIRouter()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_chunk_text(chunk: dict) -> str:
    return str(
        chunk.get("text")
        or chunk.get("content")
        or chunk.get("document")
        or chunk.get("page_content")
        or ""
    ).strip()


def normalize_feature(value: str) -> str:
    return " ".join(value.strip().lower().split())


def extract_chunk_feature(chunk: dict) -> str | None:
    chunk_text = get_chunk_text(chunk)

    if chunk_text:
        try:
            parsed_chunk = json.loads(chunk_text)
            feature = parsed_chunk.get("feature")

            if isinstance(feature, str) and feature.strip():
                return feature.strip()

        except (json.JSONDecodeError, TypeError):
            pass

        feature_match = re.search(
            r'["\']feature["\']\s*:\s*["\']([^"\']+)["\']',
            chunk_text,
            re.IGNORECASE,
        )

        if feature_match:
            return feature_match.group(1).strip()

    metadata = chunk.get("metadata") or {}

    document_name = metadata.get("document_name")

    if isinstance(document_name, str) and document_name.strip():
        return document_name.strip()

    return None

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
def generate_test_cases(request: GenerationRequest, db: Session = Depends(get_db)):
    """
    Generate test cases based on feature name and relevant documents.
    Supports multiple output formats and includes quality evaluation.
    """
    try:
        retrieval_query = f"{request.feature_name}\n{request.query}"

        retrieved = RAGService.retrieve_context(
            retrieval_query,
            n_results=50,
        )

        if not retrieved:
            raise HTTPException(
                status_code=404,
                detail="No relevant documents found for the query.",
            )

        requested_feature = normalize_feature(request.feature_name)

        matching_chunks = []
        retrieved_features = []

        for chunk in retrieved:
            chunk_feature = extract_chunk_feature(chunk)

            if not chunk_feature:
                continue

            retrieved_features.append(chunk_feature)

            if normalize_feature(chunk_feature) == requested_feature:
                matching_chunks.append(chunk)

        retrieved_features = list(dict.fromkeys(retrieved_features))

        if not matching_chunks:
            available_features = (
                ", ".join(retrieved_features)
                if retrieved_features
                else "No feature metadata found"
            )

            raise HTTPException(
                status_code=422,
                detail=(
                    f'No documents matching the requested feature '
                    f'"{request.feature_name}" were found. '
                    f"Retrieved features: {available_features}."
                ),
            )

        retrieved = matching_chunks
        
        test_cases, used_provider = TestCaseGenerator.generate_test_cases(
            feature_name=request.feature_name,
            query=request.query,
            retrieved_context=retrieved,
            test_types=request.test_types,
            num_cases=request.num_cases,
            provider_name=request.provider,
        )
        requirements: List[str] = []
        chunk_texts: List[str] = []

        for chunk in retrieved:
            chunk_text = get_chunk_text(chunk)
            if chunk_text:
                chunk_texts.append(chunk_text)

        # ---------------------------------------------------------
        # 1. JSON documents
        # ---------------------------------------------------------
        for chunk_text in chunk_texts:
            try:
                parsed_chunk = json.loads(chunk_text)
            except (json.JSONDecodeError, TypeError):
                parsed_chunk = None

            if isinstance(parsed_chunk, dict):
                chunk_requirements = parsed_chunk.get("requirements", [])

                if isinstance(chunk_requirements, list):
                    requirements.extend(
                        str(requirement).strip()
                        for requirement in chunk_requirements
                        if isinstance(requirement, str)
                        and requirement.strip()
                    )

                elif isinstance(chunk_requirements, str):
                    if chunk_requirements.strip():
                        requirements.append(
                            chunk_requirements.strip()
                        )

        # ---------------------------------------------------------
        # 2. TXT / MD numbered requirements
        #
        # Supports BOTH:
        #
        # 1. Requirement one
        # 2. Requirement two
        #
        # and:
        #
        # 1. Requirement one 2. Requirement two 3. Requirement three
        # ---------------------------------------------------------
        if not requirements:
            combined_text = "\n".join(chunk_texts)

            numbered_matches = re.findall(
                r"(?:^|\s)(\d+)[.)]\s+"
                r"(.*?)"
                r"(?=(?:\s+\d+[.)]\s+)|$)",
                combined_text,
                flags=re.DOTALL,
            )

            for _, requirement_text in numbered_matches:
                cleaned = re.sub(
                    r"\s+",
                    " ",
                    requirement_text,
                ).strip()

                if len(cleaned) >= 8:
                    requirements.append(cleaned)

        # ---------------------------------------------------------
        # 3. Bullet-list fallback
        # ---------------------------------------------------------
        if not requirements:
            for chunk_text in chunk_texts:
                for line in chunk_text.splitlines():
                    stripped = line.strip()

                    if not stripped:
                        continue

                    if re.match(r"^[-*•]\s+", stripped):
                        cleaned = re.sub(
                            r"^[-*•]\s+",
                            "",
                            stripped,
                        ).strip()

                        if len(cleaned) >= 8:
                            requirements.append(cleaned)

        # ---------------------------------------------------------
        # 4. Last-resort sentence fallback
        # ---------------------------------------------------------
        if not requirements:
            combined_text = " ".join(chunk_texts)

            for part in re.split(
                r"(?<=[.!?])\s+",
                combined_text,
            ):
                cleaned = re.sub(
                    r"\s+",
                    " ",
                    part,
                ).strip()

                lower = cleaned.lower()

                if (
                    len(cleaned) >= 8
                    and lower not in {
                        "requirements",
                        "password reset requirements",
                        "login requirements",
                    }
                ):
                    requirements.append(cleaned)

        # ---------------------------------------------------------
        # Clean + deduplicate
        # ---------------------------------------------------------
        cleaned_requirements: List[str] = []
        seen_requirements: set[str] = set()

        for requirement in requirements:
            normalized = re.sub(
                r"\s+",
                " ",
                requirement,
            ).strip(" -•\t\r\n\"'[]{}")

            if len(normalized) < 8:
                continue

            signature = re.sub(
                r"[^a-z0-9]+",
                " ",
                normalized.lower(),
            ).strip()

            if not signature:
                continue

            if signature in seen_requirements:
                continue

            seen_requirements.add(signature)
            cleaned_requirements.append(normalized)

        requirements = cleaned_requirements

        evaluation = EvaluationService.evaluate_test_cases(
            test_cases=test_cases,
            requirements=requirements,
            retrieved_context=retrieved,
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
        
        # Save to History DB
        run_id = str(uuid.uuid4())
        
        db_run = GenerationRun(
            id=run_id,
            feature=request.feature_name,
            query=request.query,
            provider=used_provider,
            output_format=request.output_format,
            requested_count=request.num_cases,
            retrieved_chunks_count=len(retrieved),
            evaluation_metrics=evaluation,
            formatted_output=output.get("formatted"),
            is_pinned=False
        )
        
        db.add(db_run)
        
        for idx, tc in enumerate(test_cases, start=1):
            db_tc = GeneratedTestCase(
                run_id=run_id,
                case_index=idx,
                title=tc.get("title", f"Test {idx}"),
                type=tc.get("type", "Positive"),
                priority=tc.get("priority", "Medium"),
                expected_result=tc.get("expected_result", ""),
                confidence=tc.get("confidence", 0.0),
                preconditions=tc.get("preconditions", []),
                steps=tc.get("steps", []),
                source_references=tc.get("source_references", [])
            )
            db.add(db_tc)
            
        db.commit()

        # Add id to output so frontend knows the newly generated history id
        output["id"] = run_id
        
        return output

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Generation failed: {str(e)}",
        )

@router.get("/history", response_model=List[GenerationRunResponse])
def get_history(db: Session = Depends(get_db)):
    runs = db.query(GenerationRun).order_by(GenerationRun.created_at.desc()).all()
    return runs

@router.get("/history/{run_id}", response_model=GenerationRunDetailResponse)
def get_history_detail(run_id: str, db: Session = Depends(get_db)):
    run = db.query(GenerationRun).filter(GenerationRun.id == run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Generation run not found")
    return run

@router.delete("/history/{run_id}")
def delete_history(run_id: str, db: Session = Depends(get_db)):
    run = db.query(GenerationRun).filter(GenerationRun.id == run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Generation run not found")
    db.delete(run)
    db.commit()
    return {"status": "deleted"}

@router.patch("/history/{run_id}/pin")
def toggle_pin_history(run_id: str, db: Session = Depends(get_db)):
    run = db.query(GenerationRun).filter(GenerationRun.id == run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Generation run not found")
    run.is_pinned = not run.is_pinned
    db.commit()
    return {"status": "success", "is_pinned": run.is_pinned}

