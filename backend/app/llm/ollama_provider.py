import json
import logging
import os
import re
from typing import Any, Dict, List

try:
    import requests
except ImportError:
    requests = None

from app.llm.base_provider import LLMProvider

logger = logging.getLogger(__name__)


class OllamaProvider(LLMProvider):
    name = "ollama"

    MAX_ATTEMPTS = 3
    REQUEST_TIMEOUT = 120

    ALLOWED_TYPES = [
        "Positive",
        "Negative",
        "Edge Case",
        "Validation",
        "Security",
    ]

    ALLOWED_PRIORITIES = [
        "High",
        "Medium",
        "Low",
    ]

    def __init__(self):
        if requests is None:
            raise ImportError("requests package is not installed")

        self.base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/")
        self.model = os.getenv("OLLAMA_MODEL", "llama2")

    # ============================================================
    # PUBLIC GENERATION
    # ============================================================

    def generate_test_cases(
            self,
            feature_name: str,
            query: str,  # Base interface için alıyoruz ama LLM'e GÖNDERMEYECEĞİZ.
            retrieved_context: List[Dict[str, Any]],
            test_types: List[str],
            num_cases: int,
    ) -> List[Dict[str, Any]]:

        if num_cases <= 0:
            raise ValueError("num_cases must be greater than zero")

        if not retrieved_context:
            raise ValueError("No retrieved context was supplied to Ollama.")

        allowed_test_types = self._prepare_test_types(test_types)

        target_requirements = self._select_target_requirements(
            retrieved_context=retrieved_context,
            num_cases=num_cases
        )

        response_schema = self._build_single_case_schema(allowed_test_types)
        final_test_cases = []

        for i, (chunk_index, context_item) in enumerate(target_requirements, start=1):
            logger.info("Generating case %s/%s based on chunk R%s", i, num_cases, chunk_index + 1)

            case_result = self._generate_single_case_with_retry(
                feature_name=feature_name,
                context_item=context_item,
                test_types=allowed_test_types,
                response_schema=response_schema,
                chunk_index=chunk_index,
                case_number=i
            )

            final_test_cases.append(case_result)

        return final_test_cases

    def _generate_single_case_with_retry(
            self,
            feature_name: str,
            context_item: Dict[str, Any],
            test_types: List[str],
            response_schema: Dict[str, Any],
            chunk_index: int,
            case_number: int
    ) -> Dict[str, Any]:

        requirement_text = str(context_item.get("text", "")).strip()



        base_prompt = self._build_single_case_prompt(
            feature_name=feature_name,
            requirement_text=requirement_text,
            test_types=test_types,
        )

        last_error = None

        for attempt in range(1, self.MAX_ATTEMPTS + 1):
            prompt = base_prompt
            if attempt > 1:
                prompt += (
                    "\n\nRETRY INSTRUCTION:\n"
                    "Your previous response failed validation. "
                    "Generate the case again using ONLY behavior explicitly stated "
                    "in the TARGET REQUIREMENT. "
                    "Do not introduce related workflow behavior from other requirements. "
                    "Do not add login, logout, email delivery, redirects, account changes, "
                    "or other actions unless the TARGET REQUIREMENT explicitly mentions them. "
                    "Return exactly ONE valid JSON object matching the schema."
                )

            try:
                raw_text = self._call_ollama(
                    prompt=prompt,
                    response_schema=response_schema,
                )

                parsed_case = self._parse_single_response(raw_text)

                parsed_case["_requirement_text"] = requirement_text

                normalized = self._normalize_case_fields(
                    parsed_case,
                    test_types,
                )

                if len(normalized.get("steps", [])) < 3:
                    raise ValueError(
                        "Generated test case has fewer than 3 valid steps after normalization."
                    )

                self._validate_contradiction(requirement_text, normalized["expected_result"])
                self._validate_semantic_grounding(
                    requirement_text=requirement_text,
                    case=normalized,
                )

                final_case = self._attach_source_reference(
                    case=normalized,
                    context_item=context_item,
                    chunk_index=chunk_index
                )

                return final_case

            except Exception as exc:
                last_error = exc
                logger.warning("Attempt %s failed for case %s: %s", attempt, case_number, exc)

        raise ValueError(
            f"Failed to generate valid test case for requirement R{chunk_index + 1} "
            f"after {self.MAX_ATTEMPTS} attempts. Last error: {last_error}"
        )

    # ============================================================
    # PROMPT (One-Shot Example & No Query)
    # ============================================================

    def _build_single_case_prompt(
            self,
            feature_name: str,
            requirement_text: str,
            test_types: List[str],
    ) -> str:

        test_types_str = ", ".join(test_types)

        return (
            "You are a strict, literal QA automation engineer. "
            "Your ONLY job is to write EXACTLY ONE test case for the SINGLE requirement provided below.\n\n"

            f"FEATURE: {feature_name}\n\n"

            "TARGET REQUIREMENT TO TEST:\n"
            f"\"{requirement_text}\"\n\n"

            "RULES:\n"
            "1. ONLY test the specific behavior described in the TARGET REQUIREMENT.\n"
            "2. STOP the test immediately after verifying this exact requirement. Do not add end-to-end steps (like checking emails or logging in) unless explicitly stated in the target requirement.\n"
            "3. If the requirement says 'must not', 'reject', 'not allow', or 'no longer accepted', "
            "the expected_result MUST explicitly describe rejection or prevention. "
            "If the requirement only defines an expiration or time limit, verify that exact expiration behavior instead.\n"
            f"4. Allowed types: {test_types_str}\n"
            "5. Return ONLY a single JSON object. Do not wrap it in an array.\n\n"
            "6. The expected_result must describe ONLY the observable behavior stated by the target requirement.\n"
            "7. Do not add navigation, logout, login redirects, emails, account state changes, or other behavior unless explicitly stated in the target requirement.\n"
            "8. Every step must be a real executable action or verification step. Never output JSON punctuation such as ']', '},' or similar text as a step.\n"
            "9. If the requirement describes a validation rule, test that exact validation rule and all constraints explicitly listed in it.\n"
            "10. Every explicit constraint listed in the TARGET REQUIREMENT must be covered by the test case.\n"
            "11. Do not claim that an error message, notification, redirect, status change, or other UI behavior occurs unless the TARGET REQUIREMENT explicitly states it.\n"
            "12. Do not replace the subject of the requirement with a related concept. For example, if the requirement describes a password rule, the steps must operate on the password itself, not on a password reset request.\n"

            "EXAMPLE OF EXPECTED ISOLATION LEVEL:\n"
"Target Requirement: 'The system must reject values below the minimum allowed limit.'\n"
"{\n"
'  "title": "Reject value below minimum limit",\n'
'  "type": "Validation",\n'
'  "priority": "High",\n'
'  "preconditions": ["The relevant form is available"],\n'
'  "steps": [\n'
'    "Open the form containing the validated field",\n'
'    "Enter a value below the documented minimum limit",\n'
'    "Submit the form"\n'
'  ],\n'
'  "expected_result": "The system rejects the value and does not complete the operation.",\n'
'  "confidence": 0.95\n'
"}\n\n"

            "Now, generate the JSON object for the TARGET REQUIREMENT."
        )

    # ============================================================
    # REQUIREMENT SELECTION
    # ============================================================

    def _select_target_requirements(
            self,
            retrieved_context: List[Dict[str, Any]],
            num_cases: int
    ) -> List[tuple[int, Dict[str, Any]]]:

        valid_contexts = []

        seen_texts = set()

        for idx, ctx in enumerate(retrieved_context):
            text = re.sub(
                r"\s+",
                " ",
                str(ctx.get("text", "")).strip()
            )

            if not text:
                continue

            # Remove markdown/header noise from comparison.
            signature = re.sub(
                r"[^a-z0-9]+",
                " ",
                text.lower()
            ).strip()

            if signature in seen_texts:
                continue

            seen_texts.add(signature)
            valid_contexts.append((idx, ctx))

        if not valid_contexts:
            raise ValueError(
                "No valid requirements found in retrieved context."
            )

        if num_cases > len(valid_contexts):
            raise ValueError(
                f"Requested {num_cases} test cases but only "
                f"{len(valid_contexts)} distinct requirements are available."
            )

        # Prefer requirements with explicit validation / rejection /
        # boundary behavior so cases are not all positive.
        def requirement_priority(item):
            _, ctx = item
            text = str(ctx.get("text", "")).lower()

            if any(keyword in text for keyword in [
                "must not",
                "reject",
                "invalid",
                "expire",
                "no longer",
                "at least",
                "must contain",
                "must exactly",
            ]):
                return 0

            return 1

        ranked = sorted(
            valid_contexts,
            key=requirement_priority,
        )

        return ranked[:num_cases]

    # ============================================================
    # OLLAMA REQUEST
    # ============================================================

    def _call_ollama(self, prompt: str, response_schema: Dict[str, Any]) -> str:
        url = f"{self.base_url}/api/generate"

        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "format": response_schema,
            "options": {
                "temperature": 0.1,
                "num_predict": 800,
            },
        }

        try:
            response = requests.post(url, json=payload, timeout=self.REQUEST_TIMEOUT)
            response.raise_for_status()
        except requests.RequestException as exc:
            raise RuntimeError(f"Ollama request failed: {exc}") from exc

        text = response.json().get("response", "").strip()
        if not text:
            raise ValueError("Ollama returned an empty response.")

        return text

    # ============================================================
    # JSON SCHEMA
    # ============================================================

    def _build_single_case_schema(self, test_types: List[str]) -> Dict[str, Any]:
        return {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "title": {"type": "string", "minLength": 5},
                "type": {"type": "string", "enum": test_types},
                "priority": {"type": "string", "enum": self.ALLOWED_PRIORITIES},
                "preconditions": {
                    "type": "array",
                    "minItems": 1,
                    "items": {"type": "string", "minLength": 3}
                },
                "steps": {
                    "type": "array",
                    "minItems": 3,
                    "items": {"type": "string", "minLength": 3}
                },
                "expected_result": {"type": "string", "minLength": 5},
                "confidence": {"type": "number", "minimum": 0, "maximum": 1}
            },
            "required": [
                "title", "type", "priority", "preconditions", "steps", "expected_result", "confidence"
            ]
        }

    # ============================================================
    # PARSING & NORMALIZATION
    # ============================================================

    def _parse_single_response(self, text: str) -> Dict[str, Any]:
        cleaned_text = text.strip()
        fence_match = re.search(r"```(?:json)?\s*([\s\S]*?)```", cleaned_text, flags=re.IGNORECASE)

        if fence_match:
            cleaned_text = fence_match.group(1).strip()

        try:
            data = json.loads(cleaned_text)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid JSON returned: {cleaned_text[:200]}") from exc

        if isinstance(data, list):
            if not data:
                raise ValueError("Model returned an empty list.")
            data = data[0]

        if not isinstance(data, dict):
            raise ValueError("Model must return a JSON object.")

        return data

    def _normalize_case_fields(self, case: Dict[str, Any], allowed_test_types: List[str]) -> Dict[str, Any]:
        normalized = dict(case)
        normalized["title"] = str(case.get("title", "")).strip()
        normalized["expected_result"] = str(case.get("expected_result", "")).strip()

        normalized["type"] = self._infer_test_type(
            requirement_text=str(case.get("_requirement_text", "")),
            allowed_test_types=allowed_test_types,
            model_type=case.get("type", ""),
        )

        prio_str = str(case.get("priority", "")).strip().capitalize()
        normalized["priority"] = prio_str if prio_str in self.ALLOWED_PRIORITIES else "Medium"

        normalized["preconditions"] = self._normalize_string_list(case.get("preconditions", []))
        normalized["steps"] = self._normalize_string_list(case.get("steps", []))

        try:
            normalized["confidence"] = max(
                0.0,
                min(float(case.get("confidence", 0.9)), 1.0)
            )
        except (TypeError, ValueError):
            normalized["confidence"] = 0.9

        normalized.pop("_requirement_text", None)

        return normalized

    def _validate_contradiction(
            self,
            req_text: str,
            expected_result: str
    ) -> None:

        req_lower = req_text.lower()
        exp_lower = expected_result.lower()

        rejection_requirement_patterns = [
            "must not",
            "must reject",
            "not allow",
            "must no longer",
            "cannot",
            "must be rejected",
        ]

        success_phrases = [
            "successfully completes",
            "successfully accepts",
            "successfully allows",
            "is accepted",
            "is allowed",
            "operation succeeds",
        ]

        requires_rejection = any(
            pattern in req_lower
            for pattern in rejection_requirement_patterns
        )

        indicates_success = any(
            phrase in exp_lower
            for phrase in success_phrases
        )

        if requires_rejection and indicates_success:
            raise ValueError(
                "Contradiction detected: requirement prohibits or rejects "
                "the behavior, but expected_result indicates success."
            )

    def _validate_semantic_grounding(
            self,
            requirement_text: str,
            case: Dict[str, Any],
    ) -> None:

        requirement = requirement_text.lower()

        case_text = " ".join([
            str(case.get("title", "")),
            " ".join(case.get("preconditions", [])),
            " ".join(case.get("steps", [])),
            str(case.get("expected_result", "")),
        ]).lower()

        suspicious_behaviors = {
            "log out": [
                "log out",
                "logout",
                "logged out",
            ],
            "error message": [
                "error message",
                "error notification",
                "displays an error",
                "shows an error",
            ],
            "send email": [
                "send email",
                "email is sent",
                "sent to the email",
                "registered email address",
                "retrieve the password reset link from",
            ],
            "login": [
                "login page",
                "log in",
                "login succeeds",
            ],
            "redirect": [
                "redirect",
                "navigates to",
            ],
            "account creation": [
                "create account",
                "account is created",
            ],
        }

        for behavior_name, phrases in suspicious_behaviors.items():
            behavior_used = any(
                phrase in case_text
                for phrase in phrases
            )

            behavior_supported = any(
                phrase in requirement
                for phrase in phrases
            )

            if behavior_used and not behavior_supported:
                raise ValueError(
                    f"Semantic grounding failed: generated case introduces "
                    f"unsupported behavior '{behavior_name}'."
                )

        # Detect valid-input / rejection contradictions.
        positive_input_phrases = [
            "meets the requirement",
            "meets the requirements",
            "valid password",
            "valid value",
            "same password",
            "matching password",
            "matches the new password",
        ]

        rejection_phrases = [
            "reject",
            "rejected",
            "does not complete",
            "not accepted",
        ]

        case_steps = " ".join(case.get("steps", [])).lower()
        expected = str(case.get("expected_result", "")).lower()

        uses_valid_input = any(
            phrase in case_steps
            for phrase in positive_input_phrases
        )

        expects_rejection = any(
            phrase in expected
            for phrase in rejection_phrases
        )

        if uses_valid_input and expects_rejection:
            raise ValueError(
                "Semantic grounding failed: test steps use valid or matching input "
                "but expected_result describes rejection."
            )

        # Detect invalid-input / acceptance contradictions.
        invalid_input_phrases = [
            "does not match",
            "different password",
            "invalid password",
            "invalid value",
            "less than",
            "below the minimum",
            "missing",
        ]

        acceptance_phrases = [
            "accepts",
            "accepted",
            "successfully",
            "completes the operation",
        ]

        uses_invalid_input = any(
            phrase in case_steps
            for phrase in invalid_input_phrases
        )

        expects_acceptance = any(
            phrase in expected
            for phrase in acceptance_phrases
        )

        if uses_invalid_input and expects_acceptance:
            raise ValueError(
                "Semantic grounding failed: test steps use invalid or mismatching input "
                "but expected_result describes acceptance."
            )

    def _attach_source_reference(
            self,
            case: Dict[str, Any],
            context_item: Dict[str, Any],
            chunk_index: int
    ) -> Dict[str, Any]:

        metadata = context_item.get("metadata", {}) or {}
        document_name = str(metadata.get("document_name", "Unknown"))
        quote = str(context_item.get("text", "")).strip()


        case["source_references"] = [{
            "document_name": document_name,
            "chunk_id": f"R{chunk_index + 1}",
            "quote": quote
        }]
        return case

    @staticmethod
    def _normalize_string_list(value: Any) -> List[str]:
        if isinstance(value, list):
            raw_items = value

        elif isinstance(value, str):
            raw_items = re.split(r"\n+", value)

        else:
            return []

        cleaned_items = []

        for item in raw_items:
            cleaned = re.sub(
                r"^\s*(?:[-*•]|\d+[.)])\s*",
                "",
                str(item),
            ).strip()

            if not cleaned:
                continue

            # Remove malformed JSON artifacts accidentally emitted as steps.
            if re.fullmatch(
                    r"[\[\]\{\},:]+",
                    cleaned,
            ):
                continue

            if cleaned in {
                "]",
                "],",
                "[",
                "[,",
                "}",
                "},",
            }:
                continue

            cleaned_items.append(cleaned)

        return cleaned_items

    def _prepare_test_types(self, test_types: List[str]) -> List[str]:
        if not test_types:
            return ["Positive", "Negative", "Edge Case"]

        cleaned = [str(t).strip() for t in test_types if str(t).strip() in self.ALLOWED_TYPES]
        cleaned = list(dict.fromkeys(cleaned))
        return cleaned if cleaned else ["Positive", "Negative", "Edge Case"]

    def _infer_test_type(
            self,
            requirement_text: str,
            allowed_test_types: List[str],
            model_type: Any = "",
    ) -> str:
        req = requirement_text.lower()

        if any(
                phrase in req
                for phrase in [
                    "must reject",
                    "must not",
                    "must no longer",
                    "not allow",
                    "cannot",
                    "not associated",
                ]
        ):
            preferred = "Negative"

        elif any(
                phrase in req
                for phrase in [
                    "valid format",
                    "must contain",
                    "must exactly match",
                    "at least",
                ]
        ):
            preferred = "Validation"

        elif any(
                phrase in req
                for phrase in [
                    "expire after",
                    "expired",
                    "boundary",
                ]
        ):
            preferred = "Edge Case"

        else:
            preferred = "Positive"

        if preferred in allowed_test_types:
            return preferred

        model_type_str = str(model_type).strip()

        if model_type_str in allowed_test_types:
            return model_type_str

        return allowed_test_types[0]