import json
import re
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.services.rag_service import RAGService
from app.services.generation_service import TestCaseGenerator
from app.services.evaluation_service import EvaluationService
from app.schemas.generation import GenerationRequestSchema, GenerationResponseSchema
from typing import List


router = APIRouter()

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
def generate_test_cases(request: GenerationRequest):
    """
    Generate test cases based on feature name and relevant documents.
    Supports multiple output formats and includes quality evaluation.
    """
    try:
        retrieval_query = f"{request.feature_name}\n{request.query}"

        retrieved = RAGService.retrieve_context(
            retrieval_query,
            n_results=10,
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


        for chunk_text in chunk_texts:
            try:
                parsed_chunk = json.loads(chunk_text)
            except (json.JSONDecodeError, TypeError):
                continue

            if not isinstance(parsed_chunk, dict):
                continue

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
                    requirements.append(chunk_requirements.strip())


        if not requirements:
            combined_chunk_text = "\n".join(chunk_texts)

            requirements_start = re.search(
                r'"requirements"\s*:\s*\[',
                combined_chunk_text,
                flags=re.IGNORECASE,
            )

            if requirements_start:
                requirements_section = combined_chunk_text[
                    requirements_start.end():
                ]

                # Dizinin kapanışına kadar olan bölümü kullan.
                closing_bracket = requirements_section.find("]")

                if closing_bracket != -1:
                    requirements_section = requirements_section[:closing_bracket]

                extracted_values = re.findall(
                    r'"((?:\\.|[^"\\])*)"',
                    requirements_section,
                )

                requirements.extend(
                    value.replace('\\"', '"').strip()
                    for value in extracted_values
                    if value.strip()
                )


        if not requirements:
            for chunk_text in chunk_texts:
                for line in chunk_text.splitlines():
                    stripped = line.strip()

                    if not stripped:
                        continue

                    if re.match(r"^([-*•]|\d+[.)])\s+", stripped):
                        cleaned_line = re.sub(
                            r"^([-*•]|\d+[.)])\s+",
                            "",
                            stripped,
                        ).strip()

                        if len(cleaned_line) >= 8:
                            requirements.append(cleaned_line)


        cleaned_requirements: List[str] = []
        seen_requirements: set[str] = set()

        for requirement in requirements:
            normalized = re.sub(
                r"\s+",
                " ",
                requirement,
            ).strip(" -•\t\r\n\"'[]{}")

            lower = normalized.lower()

            if len(normalized) < 8:
                continue


            if (
                lower.startswith("generate comprehensive")
                or lower.startswith("generate test cases")
                or lower.startswith("create test cases")
                or lower.startswith("write test cases")
            ):
                continue


            duplicate_email_phrases = [
                "duplicate email",
                "already registered email",
                "email already registered",
                "email is already registered",
                "email already exists",
                "email address already exists",
                "email address is already registered",
            ]

            if any(
                phrase in lower
                for phrase in duplicate_email_phrases
            ):
                normalized = "Duplicate email addresses must be rejected."
                lower = normalized.lower()

            signature = re.sub(
                r"[^a-z0-9]+",
                " ",
                lower,
            ).strip()

            if not signature or signature in seen_requirements:
                continue

            seen_requirements.add(signature)
            cleaned_requirements.append(normalized)

        requirements = cleaned_requirements

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
