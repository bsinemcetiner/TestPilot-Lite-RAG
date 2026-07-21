import json
import re
from itertools import product
from typing import Any, Dict, List

from app.llm.base_provider import LLMProvider


class MockLLMProvider(LLMProvider):
    """
    Deterministic local provider used when no external LLM is configured.

    This provider does not call an AI model. It extracts simple requirements
    from the retrieved RAG context and turns them into structured test cases.
    """

    name = "mock"

    ALLOWED_TYPES = [
        "Positive",
        "Negative",
        "Edge Case",
        "Validation",
        "Security",
    ]

    def generate_test_cases(
            self,
            feature_name: str,
            query: str,
            retrieved_context: List[Dict[str, Any]],
            test_types: List[str],
            num_cases: int,
    ) -> List[Dict[str, Any]]:
        available_types = [
            test_type
            for test_type in test_types
            if test_type in self.ALLOWED_TYPES
        ]

        if not available_types:
            available_types = [
                "Positive",
                "Negative",
                "Edge Case",
            ]

        requirements = self._extract_requirements(
            retrieved_context
        )

        if not requirements:
            requirements = [
                query.strip()
                or f"{feature_name} should work as expected."
            ]

        source_references = self._build_source_references(
            retrieved_context
        )

        cases: List[Dict[str, Any]] = []
        used_signatures: set[str] = set()

        # Requirement'ları anlamsal olarak uygun test türleriyle eşleştir.
        for requirement in requirements:
            recommended_types = (
                self._recommended_types_for_requirement(
                    requirement=requirement,
                    available_types=available_types,
                )
            )

            for test_type in recommended_types:
                if len(cases) >= num_cases:
                    break

                case = self._build_case(
                    index=len(cases) + 1,
                    feature_name=feature_name,
                    test_type=test_type,
                    requirement=requirement,
                    source_references=source_references,
                )

                signature = self._case_signature(case)

                if signature in used_signatures:
                    continue

                used_signatures.add(signature)
                cases.append(case)

            if len(cases) >= num_cases:
                break

        # Ana requirement senaryoları yeterli değilse
        # farklı test varyasyonları üret.
        variant_number = 1
        maximum_attempts = num_cases * 10

        while (
                len(cases) < num_cases
                and variant_number <= maximum_attempts
        ):
            requirement = requirements[
                (variant_number - 1) % len(requirements)
                ]

            test_type = available_types[
                (variant_number - 1) % len(available_types)
                ]

            case = self._build_variant_case(
                index=len(cases) + 1,
                feature_name=feature_name,
                test_type=test_type,
                requirement=requirement,
                source_references=source_references,
                variant_number=variant_number,
            )

            signature = self._case_signature(case)
            variant_number += 1

            if signature in used_signatures:
                continue

            used_signatures.add(signature)
            cases.append(case)

        # ID'leri son listeye göre yeniden düzenle.
        for index, case in enumerate(cases, start=1):
            case["id"] = index

            title = str(case.get("title", ""))
            title = re.sub(
                r"\s*\(Case\s+\d+\)\s*$",
                "",
                title,
                flags=re.IGNORECASE,
            )

            case["title"] = f"{title} (Case {index})"

        return cases

    def _extract_requirements(
        self,
        retrieved_context: List[Dict[str, Any]],
    ) -> List[str]:
        requirements: List[str] = []

        for context in retrieved_context:
            text = str(context.get("text", "")).strip()

            if not text:
                continue

            requirements.extend(self._extract_from_json(text))
            requirements.extend(self._extract_from_lines(text))

        cleaned: List[str] = []

        for requirement in requirements:
            normalized = re.sub(r"\s+", " ", requirement).strip(" -•\t\r\n\"'")

            if len(normalized) < 8:
                continue

            if normalized not in cleaned:
                cleaned.append(normalized)

        return cleaned

    def _extract_from_json(self, text: str) -> List[str]:
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            return []

        results: List[str] = []

        def walk(value: Any) -> None:
            if isinstance(value, dict):
                for key, item in value.items():
                    normalized_key = str(key).lower()

                    if normalized_key in {
                        "requirements",
                        "acceptance_criteria",
                        "acceptancecriteria",
                        "criteria",
                        "rules",
                    }:
                        if isinstance(item, list):
                            for entry in item:
                                if isinstance(entry, str):
                                    results.append(entry)
                                else:
                                    walk(entry)
                        elif isinstance(item, str):
                            results.append(item)
                    else:
                        walk(item)

            elif isinstance(value, list):
                for item in value:
                    walk(item)

        walk(data)
        return results

    def _extract_from_lines(self, text: str) -> List[str]:
        results: List[str] = []

        for line in text.splitlines():
            stripped = line.strip()

            if not stripped:
                continue

            if re.match(r"^([-*•]|\d+[.)])\s+", stripped):
                stripped = re.sub(
                    r"^([-*•]|\d+[.)])\s+",
                    "",
                    stripped,
                )

                if stripped:
                    results.append(stripped)

        return results

    def _recommended_types_for_requirement(
            self,
            requirement: str,
            available_types: List[str],
    ) -> List[str]:
        """
        Requirement içeriğini inceleyerek mantıksal olarak
        uygun test türlerini seçer.
        """
        lower_requirement = requirement.lower()
        recommended: List[str] = []

        def add_if_available(test_type: str) -> None:
            if (
                    test_type in available_types
                    and test_type not in recommended
            ):
                recommended.append(test_type)

        # Hesap kilitleme ve deneme sınırları
        if any(
                keyword in lower_requirement
                for keyword in [
                    "failed attempt",
                    "locked",
                    "lock",
                    "maximum attempt",
                    "retry limit",
                ]
        ):
            add_if_available("Edge Case")
            add_if_available("Security")
            add_if_available("Negative")

        # Hatalı veri ve reddedilme senaryoları
        elif any(
                keyword in lower_requirement
                for keyword in [
                    "invalid",
                    "error",
                    "rejected",
                    "incorrect",
                    "unauthorized",
                    "must return an error",
                ]
        ):
            add_if_available("Negative")
            add_if_available("Validation")
            add_if_available("Security")

        # Zorunlu alanlar ve kullanıcı girişi
        elif any(
                keyword in lower_requirement
                for keyword in [
                    "email",
                    "password",
                    "required",
                    "must enter",
                    "mandatory",
                ]
        ):
            add_if_available("Positive")
            add_if_available("Negative")
            add_if_available("Validation")

        else:
            for test_type in available_types:
                add_if_available(test_type)

        if not recommended:
            recommended.append(available_types[0])

        return recommended

    def _build_case(
        self,
        index: int,
        feature_name: str,
        test_type: str,
        requirement: str,
        source_references: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        title = self._build_title(
            feature_name=feature_name,
            test_type=test_type,
            requirement=requirement,
            index=index,
        )

        steps, expected_result = self._build_steps(
            feature_name=feature_name,
            test_type=test_type,
            requirement=requirement,
        )

        priority = (
            "High"
            if test_type in {"Positive", "Security", "Validation"}
            else "Medium"
        )

        return {
            "id": index,
            "title": title,
            "type": test_type,
            "priority": priority,
            "preconditions": [
                f"The {feature_name} feature is available.",
                "The test environment is running.",
            ],
            "steps": steps,
            "expected_result": expected_result,
            "source_references": source_references,
            "confidence": 0.65,
        }

    def _build_title(
        self,
        feature_name: str,
        test_type: str,
        requirement: str,
        index: int,
    ) -> str:
        shortened_requirement = requirement.rstrip(".")

        if len(shortened_requirement) > 70:
            shortened_requirement = shortened_requirement[:67] + "..."

        return (
            f"{test_type} - {feature_name}: "
            f"{shortened_requirement} (Case {index})"
        )

    def _build_steps(
        self,
        feature_name: str,
        test_type: str,
        requirement: str,
    ) -> tuple[List[str], str]:
        lower_requirement = requirement.lower()

        if "email" in lower_requirement and "password" in lower_requirement:
            if test_type == "Positive":
                return (
                    [
                        f"Open the {feature_name} page.",
                        "Enter a registered email address.",
                        "Enter the correct password.",
                        "Submit the login form.",
                    ],
                    "The user is authenticated successfully and is allowed to continue.",
                )

            if test_type == "Negative":
                return (
                    [
                        f"Open the {feature_name} page.",
                        "Enter a registered email address.",
                        "Enter an incorrect password.",
                        "Submit the login form.",
                    ],
                    "The login attempt is rejected and an error message is displayed.",
                )

            if test_type == "Validation":
                return (
                    [
                        f"Open the {feature_name} page.",
                        "Leave the email or password field empty.",
                        "Submit the login form.",
                    ],
                    "Required-field validation messages are displayed and login is not attempted.",
                )

            if test_type == "Security":
                return (
                    [
                        f"Open the {feature_name} page.",
                        "Enter malicious or specially crafted input in the email and password fields.",
                        "Submit the login form.",
                    ],
                    "The input is handled safely and authentication is not bypassed.",
                )

        failed_attempt_match = re.search(
            r"(\d+)\s+failed attempts?",
            lower_requirement,
        )

        if failed_attempt_match:
            attempt_count = failed_attempt_match.group(1)

            return (
                [
                    f"Open the {feature_name} page.",
                    "Enter a valid user email address.",
                    f"Submit an incorrect password {attempt_count} consecutive times.",
                    "Attempt to sign in one more time.",
                ],
                (
                    f"The account is locked after {attempt_count} failed attempts "
                    "and further login attempts are blocked."
                ),
            )

        if "invalid credentials" in lower_requirement:
            return (
                [
                    f"Open the {feature_name} page.",
                    "Enter invalid credentials.",
                    "Submit the form.",
                ],
                "The operation is rejected and a clear error message is displayed.",
            )

        return (
            [
                f"Open the {feature_name} feature.",
                f"Prepare test data for this requirement: {requirement}",
                f"Execute the scenario as a {test_type.lower()} test.",
                "Observe the system response.",
            ],
            f"The system behaves consistently with the requirement: {requirement}",
        )

    def _case_signature(
            self,
            test_case: Dict[str, Any],
    ) -> str:
        """
        Test türü veya Case numarası farklı olsa bile,
        aynı adımlar ve beklenen sonuç aynı test kabul edilir.
        """
        steps = " ".join(
            str(step).lower().strip()
            for step in test_case.get("steps", [])
        )

        expected = str(
            test_case.get("expected_result", "")
        ).lower().strip()

        raw_signature = f"{steps}|{expected}"

        return re.sub(
            r"[^a-z0-9]+",
            " ",
            raw_signature,
        ).strip()

    def _build_variant_case(
            self,
            index: int,
            feature_name: str,
            test_type: str,
            requirement: str,
            source_references: List[Dict[str, Any]],
            variant_number: int,
    ) -> Dict[str, Any]:
        """
        Ana kombinasyonlar yeterli olmadığında birbirinden farklı
        ek test varyasyonları oluşturur.
        """
        lower_requirement = requirement.lower()

        if (
                "email" in lower_requirement
                and "password" in lower_requirement
        ):
            variants = [
                {
                    "title": (
                        f"{test_type} - {feature_name}: "
                        "Login with an unregistered email address"
                    ),
                    "steps": [
                        f"Open the {feature_name} page.",
                        "Enter an unregistered email address.",
                        "Enter a syntactically valid password.",
                        "Submit the login form.",
                    ],
                    "expected_result": (
                        "Authentication is rejected without revealing "
                        "whether the email address exists."
                    ),
                },
                {
                    "title": (
                        f"{test_type} - {feature_name}: "
                        "Login with an empty password"
                    ),
                    "steps": [
                        f"Open the {feature_name} page.",
                        "Enter a registered email address.",
                        "Leave the password field empty.",
                        "Submit the login form.",
                    ],
                    "expected_result": (
                        "A password validation message is displayed "
                        "and the login request is not completed."
                    ),
                },
                {
                    "title": (
                        f"{test_type} - {feature_name}: "
                        "Login with leading and trailing spaces"
                    ),
                    "steps": [
                        f"Open the {feature_name} page.",
                        "Enter a valid email address with leading "
                        "and trailing spaces.",
                        "Enter the correct password.",
                        "Submit the login form.",
                    ],
                    "expected_result": (
                        "The system handles whitespace according to "
                        "the defined validation rules without failing."
                    ),
                },
            ]

            variant = variants[
                (variant_number - 1) % len(variants)
                ]

            resolved_type = test_type

            if "unregistered email" in variant["title"].lower():
                if "Negative" in self.ALLOWED_TYPES:
                    resolved_type = "Negative"

            return {
                "id": index,
                "title": (
                    f"{resolved_type} - {feature_name}: "
                    "Login with an unregistered email address "
                    f"(Case {index})"
                ),
                "type": resolved_type,
                "priority": (
                    "High"
                    if test_type
                       in {
                           "Positive",
                           "Validation",
                           "Security",
                       }
                    else "Medium"
                ),
                "preconditions": [
                    f"The {feature_name} feature is available.",
                    "The test environment is running.",
                ],
                "steps": variant["steps"],
                "expected_result": variant["expected_result"],
                "source_references": source_references,
                "confidence": 0.62,
            }

        return {
            "id": index,
            "title": (
                f"{test_type} - {feature_name}: "
                f"Alternative scenario {variant_number} "
                f"(Case {index})"
            ),
            "type": test_type,
            "priority": "Medium",
            "preconditions": [
                f"The {feature_name} feature is available.",
                "The test environment is running.",
            ],
            "steps": [
                f"Open the {feature_name} feature.",
                (
                    "Prepare an alternative test dataset for the "
                    f"requirement: {requirement}"
                ),
                (
                    f"Execute variation {variant_number} as a "
                    f"{test_type.lower()} scenario."
                ),
                "Observe and record the system response.",
            ],
            "expected_result": (
                "The system responds consistently with the "
                f"documented requirement: {requirement}"
            ),
            "source_references": source_references,
            "confidence": 0.58,
        }

    def _build_source_references(
        self,
        retrieved_context: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        references: List[Dict[str, Any]] = []

        for index, context in enumerate(retrieved_context[:2], start=1):
            metadata = context.get("metadata", {})
            text = str(context.get("text", "")).strip()

            references.append(
                {
                    "document_name": metadata.get(
                        "document_name",
                        "Unknown",
                    ),
                    "chunk_id": metadata.get(
                        "chunk_id",
                        f"chunk_{index}",
                    ),
                    "quote": text[:220],
                }
            )

        return references