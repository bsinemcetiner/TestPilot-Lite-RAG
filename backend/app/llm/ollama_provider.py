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
            num_cases=num_cases,
            test_types=allowed_test_types,
        )

        response_schema = self._build_single_case_schema(allowed_test_types)
        final_test_cases = []

        for i, (chunk_index, context_item) in enumerate(target_requirements, start=1):
            stable_idx = context_item.get("metadata", {}).get("chunk_index", chunk_index)
            logger.info("Generating case %s/%s based on chunk R%s", i, num_cases, stable_idx + 1)

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

        constraints = self._extract_explicit_constraints(requirement_text)

        base_prompt = self._build_single_case_prompt(
            feature_name=feature_name,
            requirement_text=requirement_text,
            test_types=test_types,
            constraints=constraints,
        )

        last_error = None

        for attempt in range(1, self.MAX_ATTEMPTS + 1):
            prompt = base_prompt
            if attempt > 1 and last_error is not None:
                error_detail = str(last_error)
                retry_instruction = (
                    f"\n\nPREVIOUS ATTEMPT FAILED BECAUSE:\n{error_detail}\n\n"
                    "Generate the case again, directly addressing the issue above. "
                    "Use ONLY behavior explicitly stated in the TARGET REQUIREMENT. "
                    "Return exactly ONE valid JSON object matching the schema."
                )
                if "Constraint coverage failed" in error_detail:
                    retry_instruction += (
                        "\n\nIMPORTANT:\n"
                        "Regenerate the complete test case and make sure every "
                        "missing constraint is explicitly mentioned in the steps "
                        "or expected result."
                    )
                if "Temporal contradiction" in error_detail:
                    retry_instruction += (
                        "\n\nHOW TO FIX THE TEMPORAL CONTRADICTION:\n"
                        "Remove any phrase that says the action occurs 'within the "
                        "[N]-minute window' or 'before the [N] minutes expire'. "
                        "After stating that you waited [N] minutes, the window is "
                        "closed. Describe the action simply as attempting to use "
                        "the item after the expiry period, then verifying it is rejected. "
                        "Do NOT use 'within', 'before expiry', or 'during the window' "
                        "anywhere in the steps."
                    )
                prompt += retry_instruction

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
                self._validate_vague_steps(normalized.get("steps", []))
                self._validate_temporal_contradiction(normalized.get("steps", []))

                if constraints:
                    missing = self._validate_constraint_coverage(constraints, normalized)
                    if missing:
                        missing_list = "\n".join(f"- {c}" for c in missing)
                        raise ValueError(
                            f"Constraint coverage failed: the following explicit "
                            f"constraints from the requirement were not addressed:\n"
                            f"{missing_list}\n"
                            f"Every constraint listed in the requirement checklist "
                            f"must appear explicitly in the test steps or expected result."
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
            constraints: List[str] = None,
    ) -> str:

        test_types_str = ", ".join(test_types)

        constraint_section = ""
        if constraints:
            items_block = "\n".join(f"  - {c}" for c in constraints)
            checklist = (
                "\nEXPLICIT CONSTRAINT CHECKLIST (all must be addressed in the test steps):\n"
                f"{items_block}\n"
                "Every constraint above must appear explicitly in the test steps or expected result. "
                "Do not collapse them into a single vague statement.\n"
            )

            if len(constraints) >= 2:
                variations = "\n".join(
                    f'  - "{c}"'
                    for c in constraints
                )
                multi_plan = (
                    "\nMULTI-CONSTRAINT TEST PLAN:\n"
                    "Every explicit constraint listed above must be addressed in the test case.\n"
                    "The constraints to cover are:\n"
                    f"{variations}\n\n"
                    "RULES FOR MULTI-CONSTRAINT TESTS:\n"
                    "- Each constraint must appear as a clearly labeled step or sub-scenario.\n"
                    "- Multiple invalid variations may be represented as separate steps "
                    "without requiring a full submit/verify cycle for each one.\n"
                    "- Do not overwrite one invalid input with another without noting "
                    "that they are separate variations.\n"
                    "- The expected result must confirm that the system rejects each violating variation.\n"
                    "- Do not invent behaviors not stated in the requirement.\n"
                )
                constraint_section = checklist + multi_plan
            else:
                constraint_section = checklist

        return (
            "You are a strict, literal QA automation engineer. "
            "Your ONLY job is to write EXACTLY ONE test case for the SINGLE requirement provided below.\n\n"

            f"FEATURE: {feature_name}\n\n"

            "TARGET REQUIREMENT TO TEST:\n"
            f"\"{requirement_text}\"\n"
            f"{constraint_section}\n"

            "RULES:\n"
            "1. ONLY test the specific behavior described in the TARGET REQUIREMENT.\n"
            "2. STOP the test immediately after verifying this exact requirement. Do not add end-to-end steps (like checking emails or logging in) unless explicitly stated in the target requirement.\n"
            "3. If the requirement says 'must not', 'reject', 'not allow', or 'no longer accepted', "
            "the expected_result MUST explicitly describe rejection or prevention. "
            "If the requirement only defines an expiration or time limit, verify that exact expiration behavior instead.\n"
            f"4. Allowed types: {test_types_str}\n"
            "5. Return ONLY a single JSON object. Do not wrap it in an array.\n"
            "6. The expected_result must describe ONLY the observable behavior stated by the target requirement.\n"
            "7. Do not add navigation, logout, login redirects, emails, account state changes, or other behavior unless explicitly stated in the target requirement.\n"
            "8. Every step must be a real executable action or verification step. Never output JSON punctuation such as ']', '},' or similar text as a step.\n"
            "9. If the requirement describes a validation rule, test that exact validation rule and all constraints explicitly listed in it.\n"
            "10. Every explicit constraint listed in the TARGET REQUIREMENT must be covered by the test case.\n"
            "11. Do not claim that an error message, notification, redirect, status change, or other UI behavior occurs unless the TARGET REQUIREMENT explicitly states it.\n"
            "12. Do not replace the subject of the requirement with a related concept. For example, if the requirement describes a password rule, the steps must operate on the password itself, not on a password reset request.\n"
            "13. If the requirement describes multiple independent invalid variations (e.g., several different ways input can fail), "
            "test each variation as its own action-submit-verify sequence. "
            "Do not enter several different invalid values before a single submit — each invalid input must be submitted and verified independently.\n"
            "14. Steps must be chronologically consistent. "
            "CRITICAL: Do NOT mix post-boundary and pre-boundary language for the same time period. "
            "If the requirement tests expiry AFTER a time limit, use this structure: "
            "(a) note that the item was created, "
            "(b) allow the time period to elapse, "
            "(c) attempt to use the item after expiry, "
            "(d) verify that it is rejected. "
            "Never write 'wait N minutes' in one step and then 'within the N-minute window' in a later step. "
            "After waiting, the window has already closed — do not describe the action as occurring inside it.\n"
            "15. Every verification step must state exactly what is being verified. "
            "Do not write generic steps such as 'Verify the system response', 'Observe the result', or 'Check behavior'. "
            "Instead, write the precise assertion, for example: 'Verify that the request is rejected' or 'Verify that the link is no longer valid'.\n"

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
            '    "Submit the form",\n'
            '    "Verify that the system rejects the value"\n'
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
            num_cases: int,
            test_types: List[str] = None,
    ) -> List[tuple[int, Dict[str, Any]]]:

        if test_types is None:
            test_types = ["Positive", "Negative", "Edge Case"]

        valid_contexts = []
        seen_texts: set = set()

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

        # Classify each requirement into per-type buckets so the generated
        # cases reflect the distribution of types the user requested.
        type_pools: Dict[str, List[tuple]] = {t: [] for t in test_types}

        for idx, ctx in valid_contexts:
            text = str(ctx.get("text", ""))
            inferred = self._infer_test_type(text, test_types)
            type_pools[inferred].append((idx, ctx))

        # Round-robin fill: take one from each type bucket in sequence until
        # we have num_cases, then restart the cycle for remaining slots.
        selected: List[tuple] = []
        exhausted = False

        while len(selected) < num_cases and not exhausted:
            made_progress = False
            for t in test_types:
                if len(selected) >= num_cases:
                    break
                pool = type_pools[t]
                if pool:
                    selected.append(pool.pop(0))
                    made_progress = True
            if not made_progress:
                exhausted = True

        if len(selected) < num_cases:
            raise ValueError(
                f"Requested {num_cases} test cases but only "
                f"{len(selected)} distinct requirements are available."
            )

        return selected[:num_cases]

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
            "think": False,
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

    # Exact-match generic step phrases that carry no testable assertion.
    _VAGUE_STEP_PHRASES = frozenset([
        "verify the system response",
        "observe the response",
        "observe the result",
        "check the result",
        "verify expected behavior",
        "check behavior",
        "observe behavior",
        "note the result",
        "check the system",
        "verify system behavior",
        "verify the result",
        "check the response",
    ])

    def _validate_vague_steps(self, steps: List[str]) -> None:
        """Reject cases whose steps contain obviously generic verification phrases."""
        for step in steps:
            normalized = step.strip().rstrip(".").lower()
            if normalized in self._VAGUE_STEP_PHRASES:
                raise ValueError(
                    f"Step quality failed: step is too vague to be a testable assertion: '{step}'. "
                    "Replace with a precise verification of the expected behavior."
                )

    # Patterns where the time limit has been EXCEEDED (post-boundary).
    _POST_BOUNDARY_PATTERNS = [
        r"after\s+(?:the\s+)?(\d+)\s*[-\s]*(minute|hour|second|day|week)",
        r"wait\s+(?:for\s+)?(\d+)\s*[-\s]*(minute|hour|second|day|week)",
        r"once\s+(\d+)\s*[-\s]*(minute|hour|second|day|week)\w*\s+(?:have|has)\s+passed",
        r"past\s+(?:the\s+)?(\d+)\s*[-\s]*(minute|hour|second|day|week)",
        r"exceed\w*\s+(?:the\s+)?(\d+)\s*[-\s]*(minute|hour|second|day|week)",
        r"after\s+the\s+(\d+)[-\s]*(minute|hour|second|day|week)",
    ]

    # Patterns where the action is claimed to still be WITHIN the limit (pre-boundary).
    _PRE_BOUNDARY_PATTERNS = [
        r"within\s+(?:the\s+)?(\d+)\s*[-\s]*(minute|hour|second|day|week)",
        r"before\s+(?:the\s+)?(\d+)\s*[-\s]*(minute|hour|second|day|week)",
        r"during\s+(?:the\s+)?(\d+)\s*[-\s]*(minute|hour|second|day|week)",
        r"in\s+the\s+(\d+)\s*[-\s]*(minute|hour|second|day|week)",
        r"still\s+within\s+(?:the\s+)?(\d+)\s*[-\s]*(minute|hour|second|day|week)",
    ]

    def _validate_temporal_contradiction(self, steps: List[str]) -> None:
        """
        Detect contradictions where steps claim the time boundary has been
        exceeded (post-boundary) AND simultaneously claim to act within the
        same boundary (pre-boundary).

        Captures "wait for 30 minutes" + "within the 30-minute window" style
        contradictions that the previous simple regex missed.
        """
        combined = " ".join(steps)

        def _extract_durations(text: str, patterns: List[str]) -> set:
            found = set()
            for pat in patterns:
                for m in re.finditer(pat, text, re.IGNORECASE):
                    number = m.group(1)
                    unit = m.group(2).lower().rstrip("s")  # normalize plural
                    found.add((number, unit))
            return found

        post = _extract_durations(combined, self._POST_BOUNDARY_PATTERNS)
        pre = _extract_durations(combined, self._PRE_BOUNDARY_PATTERNS)

        overlap = post & pre
        if overlap:
            n, unit = next(iter(overlap))
            raise ValueError(
                f"Temporal contradiction detected: the test steps claim the "
                f"{n}-{unit} limit has already passed (post-boundary phrase) "
                f"but also claim to act within that same {n}-{unit} limit "
                f"(pre-boundary phrase). Steps must be chronologically consistent."
            )

    def _extract_explicit_constraints(self, requirement_text: str) -> List[str]:
        """
        Lightweight generic extraction of explicitly enumerated constraints
        from a requirement sentence.

        Looks for comma/semicolon/"and"-separated lists introduced by common
        lead phrases such as 'must contain', 'must include', 'must have', etc.
        Returns a list of constraint strings, or empty list when none found.
        """
        lead_patterns = [
            r"must\s+contain\s+(.+)",
            r"must\s+include\s+(.+)",
            r"must\s+have\s+(.+)",
            r"must\s+consist\s+of\s+(.+)",
            r"must\s+be\s+composed\s+of\s+(.+)",
            r"containing\s+(.+)",
            r"including\s+(.+)",
        ]

        text = requirement_text.strip()

        for pattern in lead_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if not match:
                continue

            list_text = match.group(1)
            # Split on commas (with optional "and") or semicolons or standalone "and".
            raw_items = re.split(r",\s*(?:and\s+)?|;\s*|\s+and\s+", list_text)
            cleaned = [
                re.sub(r"[.\s]+$", "", item).strip()
                for item in raw_items
                if item.strip() and len(item.strip()) > 2
            ]

            if len(cleaned) >= 2:
                return cleaned

        return []

    # Generic stopwords to ignore when extracting distinguishing tokens
    # from individual constraint phrases.
    _CONSTRAINT_STOPWORDS = frozenset([
        "a", "an", "the", "at", "least", "one", "must", "contain",
        "have", "be", "is", "are", "of", "or", "and", "in", "to",
        "for", "with", "that", "this", "it", "its", "on", "by",
        "from", "as", "any", "each", "per", "some", "all", "should",
        "more", "than", "no", "not", "least",
    ])

    @staticmethod
    def _normalize_token(token: str) -> str:
        """Lowercase and strip a simple trailing 's' for basic plural normalization."""
        t = token.lower().strip()
        if len(t) > 3 and t.endswith("s"):
            t = t[:-1]
        return t

    def _constraint_tokens(self, constraint_text: str) -> List[str]:
        """Return meaningful content tokens for one constraint phrase."""
        words = re.findall(r"\b[\w]+\b", constraint_text)
        return [
            self._normalize_token(w)
            for w in words
            if self._normalize_token(w) not in self._CONSTRAINT_STOPWORDS
            and len(self._normalize_token(w)) >= 2
        ]

    def _validate_constraint_coverage(
            self,
            constraints: List[str],
            case: Dict[str, Any],
    ) -> List[str]:
        """
        Verify that every explicitly extracted constraint is addressed in the
        generated test case.

        Only steps and expected_result are checked — title and preconditions
        are not sufficient evidence that a constraint was actually tested.

        A constraint is considered covered if AT LEAST ONE of its distinctive
        non-stopword tokens appears in steps + expected_result.

        Example: "one uppercase letter" is covered if "uppercase" appears,
        even without "letter". Completely uncovered constraints (where NONE
        of their tokens appear) are returned as missing.
        Returns the list of constraint strings that are NOT covered.
        """
        if not constraints:
            return []

        case_text = " ".join([
            " ".join(case.get("steps", [])),
            str(case.get("expected_result", "")),
        ])

        case_tokens = {
            self._normalize_token(w)
            for w in re.findall(r"\b[\w]+\b", case_text)
        }

        missing = []
        for constraint in constraints:
            tokens = self._constraint_tokens(constraint)
            if not tokens:
                continue
            # ANY distinctive token is sufficient — catches completely absent constraints
            # without penalising natural paraphrasing of the exact constraint wording.
            if not any(t in case_tokens for t in tokens):
                missing.append(constraint)

        return missing

    def _attach_source_reference(
            self,
            case: Dict[str, Any],
            context_item: Dict[str, Any],
            chunk_index: int
    ) -> Dict[str, Any]:

        metadata = context_item.get("metadata", {}) or {}
        document_name = str(metadata.get("document_name", "Unknown"))
        quote = str(context_item.get("text", "")).strip()

        # Use the stable chunk_index stored in Chroma metadata rather than
        # the retrieval array position, so R-numbers never change between runs.
        stable_index = metadata.get("chunk_index", chunk_index)

        case["source_references"] = [{
            "document_name": document_name,
            "chunk_id": f"R{stable_index + 1}",
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