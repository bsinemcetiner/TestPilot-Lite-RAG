import json
import re
from typing import Any, Dict, List, Tuple

from app.llm.base_provider import LLMProvider


class MockLLMProvider(LLMProvider):
    """Deterministic local test-case generator.

    The mock provider does not call an external model. It extracts requirements
    from retrieved RAG chunks and builds feature-aware, non-duplicate test cases.
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
            available_types = ["Positive", "Negative", "Edge Case"]

        num_cases = max(1, int(num_cases or 1))

        requirements = self._extract_requirements(retrieved_context)

        has_extracted_requirements = bool(requirements)

        if not requirements:
            requirements = [
                f"{feature_name} should satisfy the documented feature requirements."
            ]

        source_references = self._build_source_references(retrieved_context)
        feature_kind = self._detect_feature_kind(
            feature_name=feature_name,
            requirements=requirements,
            query=query,
        )

        cases: List[Dict[str, Any]] = []
        used_signatures: set[str] = set()

        if has_extracted_requirements:
            for requirement in requirements:
                recommended_types = self._recommended_types_for_requirement(
                    requirement=requirement,
                    available_types=available_types,
                )

                for test_type in recommended_types:
                    if len(cases) >= num_cases:
                        break

                    case = self._build_case(
                        index=len(cases) + 1,
                        feature_name=feature_name,
                        feature_kind=feature_kind,
                        test_type=test_type,
                        requirement=requirement,
                        source_references=source_references,
                    )
                    self._append_unique(
                        cases,
                        used_signatures,
                        case,
                    )

                if len(cases) >= num_cases:
                    break

        # Then use feature-aware scenario banks to reach the requested count.
        scenario_bank = self._build_scenario_bank(
            feature_name=feature_name,
            feature_kind=feature_kind,
            requirements=requirements,
            available_types=available_types,
            source_references=source_references,
        )

        for scenario in scenario_bank:
            if len(cases) >= num_cases:
                break

            scenario["id"] = len(cases) + 1
            self._append_unique(cases, used_signatures, scenario)

        # Last resort: create requirement-specific alternatives rather than
        # cloning the same generic fallback text.
        attempt = 1
        max_attempts = max(num_cases * 20, 20)
        while len(cases) < num_cases and attempt <= max_attempts:
            requirement = requirements[(attempt - 1) % len(requirements)]
            test_type = available_types[(attempt - 1) % len(available_types)]

            alternative = self._build_requirement_alternative(
                index=len(cases) + 1,
                feature_name=feature_name,
                test_type=test_type,
                requirement=requirement,
                source_references=source_references,
                variation=attempt,
            )
            self._append_unique(cases, used_signatures, alternative)
            attempt += 1

        # Stable IDs and titles after duplicate filtering.
        for index, case in enumerate(cases[:num_cases], start=1):
            case["id"] = index
            title = re.sub(
                r"\s*\(Case\s+\d+\)\s*$",
                "",
                str(case.get("title", "")).strip(),
                flags=re.IGNORECASE,
            )
            case["title"] = f"{title} (Case {index})"

        return cases[:num_cases]

    def _append_unique(
        self,
        cases: List[Dict[str, Any]],
        signatures: set[str],
        case: Dict[str, Any],
    ) -> bool:
        signature = self._case_signature(case)
        if not signature or signature in signatures:
            return False

        signatures.add(signature)
        cases.append(case)
        return True

    def _detect_feature_kind(
        self,
        feature_name: str,
        requirements: List[str],
        query: str,
    ) -> str:
        combined = " ".join(
            [feature_name, query, *requirements]
        ).lower()
        feature_only = feature_name.lower()

        registration_keywords = {
            "registration",
            "register",
            "sign up",
            "signup",
            "create account",
            "account creation",
            "kayıt",
            "üye ol",
        }
        login_keywords = {
            "login",
            "log in",
            "sign in",
            "signin",
            "authentication",
            "authenticate",
            "giriş",
        }

        # Feature name has priority so registration documents containing words
        # such as password or authentication are not mistaken for login.
        if any(keyword in feature_only for keyword in registration_keywords):
            return "registration"
        if any(keyword in feature_only for keyword in login_keywords):
            return "login"
        if any(keyword in combined for keyword in registration_keywords):
            return "registration"
        if any(keyword in combined for keyword in login_keywords):
            return "login"
        return "generic"

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
            requirements.extend(self._extract_from_json_fragments(text))
            requirements.extend(self._extract_from_lines(text))

        cleaned: List[str] = []
        seen: set[str] = set()

        for requirement in requirements:
            normalized = re.sub(
                r"\s+",
                " ",
                str(requirement),
            ).strip(" -•\t\r\n\"'[]{}")

            lower = normalized.lower()

            if len(normalized) < 8:
                continue

            # Kullanıcının üretim promptunu requirement olarak alma.
            if (
                    lower.startswith("generate comprehensive")
                    or lower.startswith("generate test cases")
                    or lower.startswith("create test cases")
                    or lower.startswith("write test cases")
            ):
                continue

            # Duplicate email requirement'larının farklı yazımlarını
            # aynı standart requirement'a dönüştür.
            duplicate_email_phrases = [
                "duplicate email",
                "already registered email",
                "email already registered",
                "email is already registered",
                "email already exists",
                "email address already exists",
                "email address is already registered",
                "existing email address",
            ]

            if any(
                    phrase in lower
                    for phrase in duplicate_email_phrases
            ):
                normalized = (
                    "Duplicate email addresses must be rejected."
                )
                lower = normalized.lower()

            signature = re.sub(
                r"[^a-z0-9]+",
                " ",
                lower,
            ).strip()

            if not signature or signature in seen:
                continue

            seen.add(signature)
            cleaned.append(normalized)

        return cleaned

    def _extract_from_json(self, text: str) -> List[str]:
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            return []

        results: List[str] = []

        def walk(value: Any, parent_key: str = "") -> None:
            if isinstance(value, dict):
                for key, item in value.items():
                    normalized_key = str(key).lower().replace(" ", "_")
                    if normalized_key in {
                        "requirements",
                        "requirement",
                        "acceptance_criteria",
                        "acceptancecriteria",
                        "criteria",
                        "rules",
                        "business_rules",
                    }:
                        self._collect_strings(item, results)
                    else:
                        walk(item, normalized_key)
            elif isinstance(value, list):
                for item in value:
                    walk(item, parent_key)

        walk(data)
        return results

    def _extract_from_json_fragments(self, text: str) -> List[str]:
        results: List[str] = []
        key_pattern = re.compile(
            r'"(?:requirements?|acceptance_criteria|criteria|rules)"\s*:\s*\[(.*?)\]',
            flags=re.IGNORECASE | re.DOTALL,
        )

        for match in key_pattern.finditer(text):
            array_body = match.group(1)
            results.extend(
                value.replace('\\"', '"')
                for value in re.findall(r'"((?:\\.|[^"\\])*)"', array_body)
            )

        return results

    def _collect_strings(self, value: Any, output: List[str]) -> None:
        if isinstance(value, str):
            output.append(value)
        elif isinstance(value, list):
            for item in value:
                self._collect_strings(item, output)
        elif isinstance(value, dict):
            for item in value.values():
                self._collect_strings(item, output)

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
        lower_requirement = requirement.lower()
        recommended: List[str] = []

        def add(test_type: str) -> None:
            if test_type in available_types and test_type not in recommended:
                recommended.append(test_type)

        if any(
            keyword in lower_requirement
            for keyword in [
                "failed attempt",
                "locked",
                "lockout",
                "maximum attempt",
                "retry limit",
            ]
        ):
            add("Edge Case")
            add("Security")
            add("Negative")
        elif any(
            keyword in lower_requirement
            for keyword in [
                "invalid",
                "error",
                "rejected",
                "incorrect",
                "unauthorized",
                "already registered",
                "already exists",
                "duplicate",
            ]
        ):
            add("Negative")
            add("Validation")
            add("Security")
        elif any(
            keyword in lower_requirement
            for keyword in [
                "required",
                "mandatory",
                "format",
                "minimum",
                "maximum",
                "length",
                "must contain",
            ]
        ):
            add("Validation")
            add("Edge Case")
            add("Positive")
        else:
            for test_type in available_types:
                add(test_type)

        return recommended or [available_types[0]]

    def _build_case(
        self,
        index: int,
        feature_name: str,
        feature_kind: str,
        test_type: str,
        requirement: str,
        source_references: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        steps, expected_result = self._build_steps(
            feature_name=feature_name,
            feature_kind=feature_kind,
            test_type=test_type,
            requirement=requirement,
        )

        shortened = requirement.rstrip(".")
        if len(shortened) > 70:
            shortened = shortened[:67] + "..."

        return self._make_case(
            index=index,
            title=f"{test_type} - {feature_name}: {shortened}",
            test_type=test_type,
            steps=steps,
            expected_result=expected_result,
            feature_name=feature_name,
            source_references=source_references,
            confidence=0.68,
        )

    def _build_steps(
        self,
        feature_name: str,
        feature_kind: str,
        test_type: str,
        requirement: str,
    ) -> Tuple[List[str], str]:
        lower = requirement.lower()

        if feature_kind == "registration":
            if "already" in lower or "duplicate" in lower or "exists" in lower:
                return (
                    [
                        f"Open the {feature_name} page.",
                        "Enter an email address that belongs to an existing account.",
                        "Enter otherwise valid registration data.",
                        "Submit the registration form.",
                    ],
                    "The account is not created and the user is told that the email address is already registered.",
                )

            if "email" in lower and any(word in lower for word in ["invalid", "format", "valid"]):
                if test_type in {"Negative", "Validation"}:
                    return (
                        [
                            f"Open the {feature_name} page.",
                            "Enter an email address with an invalid format.",
                            "Complete the remaining required fields with valid data.",
                            "Submit the registration form.",
                        ],
                        "An email validation message is displayed and no account is created.",
                    )

            if "password" in lower and any(
                word in lower for word in ["minimum", "length", "uppercase", "number", "special", "policy"]
            ):
                if test_type in {"Negative", "Validation", "Edge Case"}:
                    return (
                        [
                            f"Open the {feature_name} page.",
                            "Enter a new valid email address.",
                            f"Enter a password that targets this rule: {requirement}",
                            "Submit the registration form.",
                        ],
                        f"The password is accepted or rejected exactly according to the documented rule: {requirement}",
                    )

            if test_type == "Positive":
                return (
                    [
                        f"Open the {feature_name} page.",
                        "Enter a new and valid email address.",
                        "Enter a password that satisfies the password policy.",
                        "Complete all remaining required registration fields.",
                        "Submit the registration form.",
                    ],
                    f"The account is created successfully in accordance with this requirement: {requirement}",
                )
            if test_type == "Negative":
                return (
                    [
                        f"Open the {feature_name} page.",
                        f"Prepare invalid registration data targeting this requirement: {requirement}",
                        "Complete all unrelated fields with valid data.",
                        "Submit the registration form.",
                    ],
                    f"The account is not created and a clear error is shown for the violated requirement: {requirement}",
                )
            if test_type == "Validation":
                return (
                    [
                        f"Open the {feature_name} page.",
                        f"Leave blank or violate the field governed by this requirement: {requirement}",
                        "Submit the registration form.",
                    ],
                    f"A field-level validation message is displayed and registration is blocked: {requirement}",
                )
            if test_type == "Security":
                return (
                    [
                        f"Open the {feature_name} page.",
                        f"Enter malicious input in the field related to: {requirement}",
                        "Complete the remaining fields with valid data.",
                        "Submit the registration form.",
                    ],
                    "The input is safely rejected or sanitized, no code is executed, and no improper account is created.",
                )
            return (
                [
                    f"Open the {feature_name} page.",
                    f"Prepare boundary-value data for this registration rule: {requirement}",
                    "Submit the registration form.",
                    "Observe the account-creation result.",
                ],
                f"The boundary value is handled consistently with the documented registration rule: {requirement}",
            )

        if feature_kind == "login":
            failed_attempt_match = re.search(r"(\d+)\s+failed attempts?", lower)
            if failed_attempt_match:
                count = failed_attempt_match.group(1)
                return (
                    [
                        f"Open the {feature_name} page.",
                        "Enter a registered email address.",
                        f"Submit an incorrect password {count} consecutive times.",
                        "Attempt to sign in once more.",
                    ],
                    f"The account is locked after {count} failed attempts and further attempts are blocked.",
                )
            if test_type == "Positive":
                return (
                    [
                        f"Open the {feature_name} page.",
                        "Enter a registered email address.",
                        "Enter the correct password.",
                        "Submit the login form.",
                    ],
                    "The user is authenticated successfully and allowed to continue.",
                )
            if test_type == "Negative":
                return (
                    [
                        f"Open the {feature_name} page.",
                        "Enter a registered email address.",
                        "Enter an incorrect password.",
                        "Submit the login form.",
                    ],
                    "The login attempt is rejected and a clear error message is displayed.",
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
                        "Enter malicious input in the email and password fields.",
                        "Submit the login form.",
                    ],
                    "The input is handled safely and authentication is not bypassed.",
                )
            return (
                [
                    f"Open the {feature_name} page.",
                    "Enter credentials containing boundary-value formatting.",
                    "Submit the login form.",
                ],
                f"The login boundary condition is handled according to the requirement: {requirement}",
            )

        return (
            [
                f"Open the {feature_name} feature.",
                f"Prepare data that targets this requirement: {requirement}",
                f"Execute the scenario as a {test_type.lower()} test.",
                "Observe the system response.",
            ],
            f"The system behaves consistently with the requirement: {requirement}",
        )

    def _build_scenario_bank(
        self,
        feature_name: str,
        feature_kind: str,
        requirements: List[str],
        available_types: List[str],
        source_references: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        if feature_kind == "registration":
            definitions = self._registration_scenarios(feature_name)
        elif feature_kind == "login":
            definitions = self._login_scenarios(feature_name)
        else:
            definitions = self._generic_scenarios(feature_name, requirements)

        cases: List[Dict[str, Any]] = []
        for definition in definitions:
            test_type = definition["type"]
            if test_type not in available_types:
                continue

            cases.append(
                self._make_case(
                    index=0,
                    title=f"{test_type} - {feature_name}: {definition['title']}",
                    test_type=test_type,
                    steps=definition["steps"],
                    expected_result=definition["expected_result"],
                    feature_name=feature_name,
                    source_references=source_references,
                    confidence=0.66,
                )
            )

        return cases

    def _registration_scenarios(self, feature_name: str) -> List[Dict[str, Any]]:
        return [
            {
                "type": "Positive",
                "title": "Create an account with valid information",
                "steps": [
                    f"Open the {feature_name} page.",
                    "Enter a new valid email address.",
                    "Enter a password satisfying all password rules.",
                    "Complete every required registration field.",
                    "Submit the registration form.",
                ],
                "expected_result": "The account is created successfully and a registration confirmation is displayed.",
            },
            {
                "type": "Negative",
                "title": "Reject an already registered email address",
                "steps": [
                    f"Open the {feature_name} page.",
                    "Enter an email address belonging to an existing account.",
                    "Enter otherwise valid registration information.",
                    "Submit the registration form.",
                ],
                "expected_result": "No account is created and the user is informed that the email is already registered.",
            },
            {
                "type": "Negative",
                "title": "Reject mismatched password confirmation",
                "steps": [
                    f"Open the {feature_name} page.",
                    "Enter a new valid email address.",
                    "Enter different values in the password and confirmation fields.",
                    "Submit the registration form.",
                ],
                "expected_result": "Registration is blocked and a password-mismatch message is displayed.",
            },
            {
                "type": "Edge Case",
                "title": "Handle spaces around the email address",
                "steps": [
                    f"Open the {feature_name} page.",
                    "Enter a new email address with leading and trailing spaces.",
                    "Enter otherwise valid registration information.",
                    "Submit the registration form.",
                ],
                "expected_result": "The email is normalized according to the documented rule and no duplicate account is created.",
            },
            {
                "type": "Edge Case",
                "title": "Use a password at the minimum allowed length",
                "steps": [
                    f"Open the {feature_name} page.",
                    "Enter a new valid email address.",
                    "Enter a password exactly at the minimum allowed length.",
                    "Complete the remaining required fields and submit.",
                ],
                "expected_result": "The exact minimum boundary is accepted when all password-policy rules are satisfied.",
            },
            {
                "type": "Edge Case",
                "title": "Register an email containing uppercase characters",
                "steps": [
                    f"Open the {feature_name} page.",
                    "Enter a new valid email address containing uppercase characters.",
                    "Enter otherwise valid registration information.",
                    "Submit the registration form.",
                ],
                "expected_result": "Email casing is handled consistently and does not allow a duplicate representation of the same address.",
            },
            {
                "type": "Validation",
                "title": "Reject an invalid email format",
                "steps": [
                    f"Open the {feature_name} page.",
                    "Enter an email address with an invalid format.",
                    "Complete the remaining fields with valid data.",
                    "Submit the registration form.",
                ],
                "expected_result": "An email-format validation message is displayed and no account is created.",
            },
            {
                "type": "Validation",
                "title": "Reject a password-policy violation",
                "steps": [
                    f"Open the {feature_name} page.",
                    "Enter a new valid email address.",
                    "Enter a password that violates the documented password policy.",
                    "Submit the registration form.",
                ],
                "expected_result": "A password-policy validation message is displayed and no account is created.",
            },
            {
                "type": "Validation",
                "title": "Require all mandatory registration fields",
                "steps": [
                    f"Open the {feature_name} page.",
                    "Leave one mandatory registration field empty.",
                    "Complete all other fields with valid data.",
                    "Submit the registration form.",
                ],
                "expected_result": "A field-level required message is displayed and registration is not submitted.",
            },
            {
                "type": "Security",
                "title": "Prevent script injection through registration fields",
                "steps": [
                    f"Open the {feature_name} page.",
                    "Enter script-like input in a supported text field.",
                    "Complete the remaining registration fields with valid data.",
                    "Submit the registration form.",
                ],
                "expected_result": "The malicious input is rejected or safely sanitized and no script is executed.",
            },
            {
                "type": "Security",
                "title": "Avoid exposing the submitted password",
                "steps": [
                    f"Open the {feature_name} page.",
                    "Enter valid registration information and a valid password.",
                    "Submit the registration form.",
                    "Inspect the URL, response, and client-visible output.",
                ],
                "expected_result": "The password is not exposed in URLs, responses, logs, or other client-visible data.",
            },
        ]

    def _login_scenarios(self, feature_name: str) -> List[Dict[str, Any]]:
        return [
            {
                "type": "Positive",
                "title": "Sign in with valid credentials",
                "steps": [
                    f"Open the {feature_name} page.",
                    "Enter a registered email address.",
                    "Enter the correct password.",
                    "Submit the login form.",
                ],
                "expected_result": "The user is authenticated successfully and allowed to continue.",
            },
            {
                "type": "Negative",
                "title": "Reject an incorrect password",
                "steps": [
                    f"Open the {feature_name} page.",
                    "Enter a registered email address.",
                    "Enter an incorrect password.",
                    "Submit the login form.",
                ],
                "expected_result": "Authentication is rejected and a clear error message is displayed.",
            },
            {
                "type": "Negative",
                "title": "Reject an unregistered email address",
                "steps": [
                    f"Open the {feature_name} page.",
                    "Enter an unregistered email address.",
                    "Enter a syntactically valid password.",
                    "Submit the login form.",
                ],
                "expected_result": "Authentication is rejected without revealing whether the account exists.",
            },
            {
                "type": "Edge Case",
                "title": "Handle spaces around the email address",
                "steps": [
                    f"Open the {feature_name} page.",
                    "Enter a registered email address with surrounding spaces.",
                    "Enter the correct password.",
                    "Submit the login form.",
                ],
                "expected_result": "Whitespace is handled according to the documented login rules.",
            },
            {
                "type": "Validation",
                "title": "Require the password field",
                "steps": [
                    f"Open the {feature_name} page.",
                    "Enter a registered email address.",
                    "Leave the password field empty.",
                    "Submit the login form.",
                ],
                "expected_result": "A password-required message is shown and no authentication request is completed.",
            },
            {
                "type": "Security",
                "title": "Prevent authentication bypass input",
                "steps": [
                    f"Open the {feature_name} page.",
                    "Enter maliciously crafted input in the credential fields.",
                    "Submit the login form.",
                ],
                "expected_result": "The input is handled safely and authentication is not bypassed.",
            },
        ]

    def _generic_scenarios(
        self,
        feature_name: str,
        requirements: List[str],
    ) -> List[Dict[str, Any]]:
        scenarios: List[Dict[str, Any]] = []
        for requirement in requirements:
            for test_type in self.ALLOWED_TYPES:
                scenarios.append(
                    {
                        "type": test_type,
                        "title": f"Verify requirement as a {test_type.lower()} scenario",
                        "steps": [
                            f"Open the {feature_name} feature.",
                            f"Prepare {test_type.lower()} test data for: {requirement}",
                            "Execute the feature operation.",
                            "Observe the response.",
                        ],
                        "expected_result": f"The result is consistent with the requirement: {requirement}",
                    }
                )
        return scenarios

    def _build_requirement_alternative(
        self,
        index: int,
        feature_name: str,
        test_type: str,
        requirement: str,
        source_references: List[Dict[str, Any]],
        variation: int,
    ) -> Dict[str, Any]:
        dimensions = [
            "minimum boundary data",
            "maximum boundary data",
            "empty optional data",
            "unexpected but syntactically valid data",
            "repeated submission data",
            "normalized whitespace data",
            "case-variation data",
            "concurrent submission data",
        ]
        dimension = dimensions[(variation - 1) % len(dimensions)]

        return self._make_case(
            index=index,
            title=f"{test_type} - {feature_name}: {dimension.capitalize()} for documented rule",
            test_type=test_type,
            steps=[
                f"Open the {feature_name} feature.",
                f"Prepare {dimension} for this requirement: {requirement}",
                f"Execute the operation as a {test_type.lower()} scenario.",
                "Observe and record the system response.",
            ],
            expected_result=f"The {dimension} is handled consistently with the documented requirement: {requirement}",
            feature_name=feature_name,
            source_references=source_references,
            confidence=0.58,
        )

    def _make_case(
        self,
        index: int,
        title: str,
        test_type: str,
        steps: List[str],
        expected_result: str,
        feature_name: str,
        source_references: List[Dict[str, Any]],
        confidence: float,
    ) -> Dict[str, Any]:
        return {
            "id": index,
            "title": title,
            "type": test_type,
            "priority": (
                "High"
                if test_type in {"Positive", "Validation", "Security"}
                else "Medium"
            ),
            "preconditions": [
                f"The {feature_name} feature is available.",
                "The test environment is running.",
            ],
            "steps": steps,
            "expected_result": expected_result,
            "source_references": source_references,
            "confidence": confidence,
        }

    def _case_signature(self, test_case: Dict[str, Any]) -> str:
        steps = " ".join(
            str(step).lower().strip()
            for step in test_case.get("steps", [])
        )
        expected = str(test_case.get("expected_result", "")).lower().strip()
        raw_signature = f"{steps}|{expected}"
        return re.sub(r"[^a-z0-9]+", " ", raw_signature).strip()

    def _build_source_references(
        self,
        retrieved_context: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        references: List[Dict[str, Any]] = []

        for index, context in enumerate(retrieved_context[:2], start=1):
            metadata = context.get("metadata", {}) or {}
            text = str(context.get("text", "")).strip()

            references.append(
                {
                    "document_name": metadata.get("document_name", "Unknown"),
                    "chunk_id": metadata.get("chunk_id", f"chunk_{index}"),
                    "quote": text[:220],
                }
            )

        return references