import re
from typing import Any, Dict, List, Set



class EvaluationService:
    GENERIC_PHRASES = {
        "perform positive actions",
        "perform negative actions",
        "perform edge case actions",
        "perform validation actions",
        "perform security actions",
        "verify the result matches expectations",
        "do the required operation",
        "perform the action",
        "verify expected behavior",
        "system behaves as expected",
    }

    @staticmethod
    def evaluate_test_cases(
            test_cases: List[Dict[str, Any]],
            requirements: List[str] | None = None,
            retrieved_context: List[Dict[str, Any]] | None = None,
    ) -> Dict[str, Any]:
        requirements = requirements or []
        retrieved_context = retrieved_context or []
        if not test_cases:
            return {
                "total_cases": 0,
                "coverage_score": 0,
                "completeness_score": 0,
                "groundedness_score": 0,
                "uniqueness_score": 0,
                "specificity_score": 0,
                "overall_score": 0,
                "duplicate_count": 0,
                "duplicates": [],
                "issues_found": 1,
                "issues": ["No test cases to evaluate"],
                "recommendation": "Needs improvement",
            }

        total_cases = len(test_cases)
        issues: List[str] = []

        missing_title = 0
        missing_steps = 0
        insufficient_steps = 0
        missing_expected = 0
        missing_source = 0
        generic_case_count = 0
        invalid_confidence = 0

        type_distribution: Dict[str, int] = {}

        for test_case in test_cases:
            title = str(
                test_case.get("title", "")
            ).strip()

            steps = test_case.get("steps", [])
            expected = str(
                test_case.get("expected_result", "")
            ).strip()

            sources = test_case.get(
                "source_references",
                [],
            )

            if not title:
                missing_title += 1

            if not steps:
                missing_steps += 1
            elif len(steps) < 3:
                insufficient_steps += 1

            if not expected:
                missing_expected += 1

            if not sources:
                missing_source += 1

            if EvaluationService._is_generic_case(
                test_case
            ):
                generic_case_count += 1

            confidence = test_case.get("confidence")

            if (
                confidence is not None
                and (
                    not isinstance(
                        confidence,
                        (int, float),
                    )
                    or confidence < 0
                    or confidence > 1
                )
            ):
                invalid_confidence += 1

            test_type = str(
                test_case.get("type", "Unknown")
            )

            type_distribution[test_type] = (
                type_distribution.get(test_type, 0)
                + 1
            )

        duplicates = (
            EvaluationService.check_duplicates(
                test_cases
            )
        )

        duplicate_indices: Set[int] = set()

        for duplicate in duplicates:
            duplicate_indices.add(
                duplicate["index1"]
            )
            duplicate_indices.add(
                duplicate["index2"]
            )

        duplicate_case_count = len(
            duplicate_indices
        )

        completeness_score = (
            EvaluationService._calculate_completeness(
                total_cases=total_cases,
                missing_title=missing_title,
                missing_steps=missing_steps,
                insufficient_steps=insufficient_steps,
                missing_expected=missing_expected,
            )
        )

        grounded_cases = EvaluationService._count_grounded_cases(
            test_cases=test_cases,
            retrieved_context=retrieved_context,
        )

        groundedness_score = round(
            (grounded_cases / total_cases) * 100,
            2,
        ) if total_cases > 0 else 0.0

        uniqueness_score = round(
            (
                total_cases - duplicate_case_count
            )
            / total_cases
            * 100,
            2,
        )

        specificity_score = round(
            (
                total_cases - generic_case_count
            )
            / total_cases
            * 100,
            2,
        )

        coverage_result = EvaluationService._calculate_requirement_coverage(
            requirements=requirements,
            test_cases=test_cases,
        )

        coverage_score = coverage_result["score"]
        covered_requirements = coverage_result["covered_requirements"]
        uncovered_requirements = coverage_result["uncovered_requirements"]
        requirement_coverage_details = coverage_result["details"]


        overall_score = round(
            coverage_score * 0.20
            + completeness_score * 0.25
            + groundedness_score * 0.20
            + uniqueness_score * 0.20
            + specificity_score * 0.15,
            2,
        )

        if missing_title:
            issues.append(
                f"{missing_title} test case(s) missing title"
            )

        if missing_steps:
            issues.append(
                f"{missing_steps} test case(s) missing steps"
            )

        if insufficient_steps:
            issues.append(
                f"{insufficient_steps} test case(s) "
                "have fewer than 3 steps"
            )

        if missing_expected:
            issues.append(
                f"{missing_expected} test case(s) "
                "missing expected result"
            )

        if missing_source:
            issues.append(
                f"{missing_source} test case(s) "
                "missing source reference"
            )

        if generic_case_count:
            issues.append(
                f"{generic_case_count} test case(s) "
                "contain generic or non-specific steps"
            )

        if duplicates:
            issues.append(
                f"{len(duplicates)} potential duplicate "
                "pair(s) detected"
            )

        if invalid_confidence:
            issues.append(
                f"{invalid_confidence} test case(s) "
                "have invalid confidence values"
            )

        recommendation = (
            EvaluationService._get_recommendation(
                overall_score=overall_score,
                coverage_score=coverage_score,
                completeness_score=completeness_score,
                groundedness_score=groundedness_score,
                uniqueness_score=uniqueness_score,
                specificity_score=specificity_score,
                duplicate_count=len(duplicates),
            )
        )

        return {
            "total_cases": total_cases,
            "coverage_score": coverage_score,
            "completeness_score": completeness_score,
            "groundedness_score": groundedness_score,
            "uniqueness_score": uniqueness_score,
            "specificity_score": specificity_score,
            "overall_score": overall_score,
            "type_distribution": type_distribution,
            "duplicate_count": len(duplicates),
            "duplicate_case_count": duplicate_case_count,
            "duplicates": duplicates,
            "generic_case_count": generic_case_count,
            "issues_found": len(issues),
            "issues": issues,
            "recommendation": recommendation,
            "covered_requirements": covered_requirements,
            "uncovered_requirements": uncovered_requirements,
            "requirement_coverage_details": requirement_coverage_details,
        }

    @staticmethod
    def _calculate_completeness(
        total_cases: int,
        missing_title: int,
        missing_steps: int,
        insufficient_steps: int,
        missing_expected: int,
    ) -> float:
        title_score = (
            total_cases - missing_title
        ) / total_cases

        steps_score = (
            total_cases
            - missing_steps
            - insufficient_steps * 0.5
        ) / total_cases

        expected_score = (
            total_cases - missing_expected
        ) / total_cases

        steps_score = max(
            0,
            min(1, steps_score),
        )

        score = (
            title_score * 0.25
            + steps_score * 0.50
            + expected_score * 0.25
        ) * 100

        return round(score, 2)

    @staticmethod
    def _count_grounded_cases(
            test_cases: List[Dict[str, Any]],
            retrieved_context: List[Dict[str, Any]],
    ) -> int:
        if not retrieved_context:
            return 0

        context_parts = []
        for chunk in retrieved_context:
            text = str(
                chunk.get("text")
                or chunk.get("content")
                or chunk.get("document")
                or chunk.get("page_content")
                or ""
            ).strip()
            if text:
                context_parts.append(text)

        combined_context = " ".join(context_parts)
        combined_context_lower = combined_context.lower()
        context_tokens = EvaluationService._normalize_tokens(combined_context)
        context_normalized_str = " ".join(context_tokens)

        grounded_count = 0

        for test_case in test_cases:
            sources = test_case.get("source_references", [])
            if not isinstance(sources, list) or not sources:
                continue

            is_case_grounded = False
            for source in sources:
                if not isinstance(source, dict):
                    continue

                doc_name = str(source.get("document_name", "")).strip()
                quote = str(source.get("quote", "")).strip()

                if not doc_name or not quote:
                    continue

                # 1. Exact or near-exact match
                if quote.lower() in combined_context_lower:
                    is_case_grounded = True
                    break

                # 2. Strong token match
                quote_tokens = EvaluationService._normalize_tokens(quote)
                if not quote_tokens:
                    continue

                quote_normalized_str = " ".join(quote_tokens)
                if quote_normalized_str in context_normalized_str:
                    is_case_grounded = True
                    break

                # 3. High intersection ratio
                common = quote_tokens.intersection(context_tokens)
                if len(common) / len(quote_tokens) >= 0.7:
                    is_case_grounded = True
                    break

            if is_case_grounded:
                grounded_count += 1

        return grounded_count

    @staticmethod
    def _calculate_coverage(
        type_distribution: Dict[str, int],
        total_cases: int,
    ) -> float:
        supported_types = {
            "Positive",
            "Negative",
            "Edge Case",
            "Validation",
            "Security",
        }

        represented_types = (
            set(type_distribution.keys())
            & supported_types
        )

        type_variety_score = (
            len(represented_types)
            / len(supported_types)
            * 100
        )

        if total_cases <= 1:
            balance_score = 100.0
        else:
            counts = [
                type_distribution[test_type]
                for test_type in represented_types
            ]

            if not counts:
                balance_score = 0.0
            else:
                maximum = max(counts)
                minimum = min(counts)

                balance_score = (
                    minimum / maximum * 100
                    if maximum
                    else 0
                )

        return round(
            type_variety_score * 0.70
            + balance_score * 0.30,
            2,
        )

    @staticmethod
    def _is_generic_case(
        test_case: Dict[str, Any],
    ) -> bool:
        searchable_parts = [
            str(test_case.get("title", "")),
            str(
                test_case.get(
                    "expected_result",
                    "",
                )
            ),
        ]

        searchable_parts.extend(
            str(step)
            for step in test_case.get(
                "steps",
                [],
            )
        )

        combined_text = " ".join(
            searchable_parts
        ).lower()

        normalized_text = re.sub(
            r"\s+",
            " ",
            combined_text,
        ).strip()

        for phrase in (
            EvaluationService.GENERIC_PHRASES
        ):
            if phrase in normalized_text:
                return True

        meaningful_words = {
            word
            for word in re.findall(
                r"[a-zA-Z0-9]+",
                normalized_text,
            )
            if len(word) >= 4
        }

        return len(meaningful_words) < 8

    @staticmethod
    def check_duplicates(
        test_cases: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        duplicates: List[
            Dict[str, Any]
        ] = []

        for first_index in range(
            len(test_cases)
        ):
            for second_index in range(
                first_index + 1,
                len(test_cases),
            ):
                first_case = test_cases[first_index]
                second_case = test_cases[second_index]

                title_similarity = (
                    EvaluationService._text_similarity(
                        str(
                            first_case.get(
                                "title",
                                "",
                            )
                        ),
                        str(
                            second_case.get(
                                "title",
                                "",
                            )
                        ),
                    )
                )

                steps_similarity = (
                    EvaluationService._list_similarity(
                        first_case.get(
                            "steps",
                            [],
                        ),
                        second_case.get(
                            "steps",
                            [],
                        ),
                    )
                )

                expected_similarity = (
                    EvaluationService._text_similarity(
                        str(
                            first_case.get(
                                "expected_result",
                                "",
                            )
                        ),
                        str(
                            second_case.get(
                                "expected_result",
                                "",
                            )
                        ),
                    )
                )

                combined_similarity = (
                    title_similarity * 0.25
                    + steps_similarity * 0.50
                    + expected_similarity * 0.25
                )

                exact_steps_match = (
                    EvaluationService._normalize_list(
                        first_case.get(
                            "steps",
                            [],
                        )
                    )
                    == EvaluationService._normalize_list(
                        second_case.get(
                            "steps",
                            [],
                        )
                    )
                )

                if (
                    combined_similarity >= 0.78
                    or exact_steps_match
                ):
                    duplicates.append(
                        {
                            "index1": first_index,
                            "index2": second_index,
                            "case1_id": first_case.get(
                                "id",
                                first_index + 1,
                            ),
                            "case2_id": second_case.get(
                                "id",
                                second_index + 1,
                            ),
                            "case1": first_case.get(
                                "title",
                                "",
                            ),
                            "case2": second_case.get(
                                "title",
                                "",
                            ),
                            "title_similarity": round(
                                title_similarity,
                                2,
                            ),
                            "steps_similarity": round(
                                steps_similarity,
                                2,
                            ),
                            "expected_similarity": round(
                                expected_similarity,
                                2,
                            ),
                            "similarity": round(
                                combined_similarity,
                                2,
                            ),
                        }
                    )

        return duplicates

    @staticmethod
    def _normalize_text(
        text: str,
    ) -> Set[str]:
        normalized = re.sub(
            r"[^a-zA-Z0-9\s]",
            " ",
            text.lower(),
        )

        return {
            word
            for word in normalized.split()
            if len(word) >= 3
        }

    @staticmethod
    def _normalize_list(
        values: List[Any],
    ) -> List[str]:
        return [
            re.sub(
                r"\s+",
                " ",
                str(value).lower(),
            ).strip()
            for value in values
        ]

    @staticmethod
    def _text_similarity(
        text1: str,
        text2: str,
    ) -> float:
        words1 = (
            EvaluationService._normalize_text(
                text1
            )
        )
        words2 = (
            EvaluationService._normalize_text(
                text2
            )
        )

        if not words1 or not words2:
            return 0.0

        intersection = len(
            words1 & words2
        )
        union = len(
            words1 | words2
        )

        return (
            intersection / union
            if union
            else 0.0
        )

    @staticmethod
    def _list_similarity(
        values1: List[Any],
        values2: List[Any],
    ) -> float:
        text1 = " ".join(
            str(value)
            for value in values1
        )
        text2 = " ".join(
            str(value)
            for value in values2
        )

        return (
            EvaluationService._text_similarity(
                text1,
                text2,
            )
        )

    @staticmethod
    def _calculate_requirement_coverage(
            requirements: List[str],
            test_cases: List[Dict[str, Any]],
    ) -> Dict[str, Any]:

        clean_requirements = [
            str(requirement).strip()
            for requirement in requirements
            if str(requirement).strip()
        ]

        if not clean_requirements:
            return {
                "score": 0.0,
                "covered_requirements": [],
                "uncovered_requirements": [],
                "details": [],
            }

        covered_requirements: List[str] = []
        uncovered_requirements: List[str] = []
        details: List[Dict[str, Any]] = []

        for requirement in clean_requirements:
            best_score = 0.0
            best_case_title = None

            for test_case in test_cases:
                match_score = EvaluationService._requirement_match_score(
                    requirement=requirement,
                    test_case=test_case,
                )

                if match_score > best_score:
                    best_score = match_score
                    best_case_title = str(
                        test_case.get(
                            "title",
                            "Untitled test case",
                        )
                    )

            is_covered = best_score >= 0.60

            if is_covered:
                covered_requirements.append(requirement)
            else:
                uncovered_requirements.append(requirement)

            details.append(
                {
                    "requirement": requirement,
                    "covered": is_covered,
                    "match_score": round(best_score, 2),
                    "matched_test_case": (
                        best_case_title
                        if is_covered
                        else None
                    ),
                }
            )

        coverage_score = (
                len(covered_requirements)
                / len(clean_requirements)
                * 100
        )

        return {
            "score": round(coverage_score, 2),
            "covered_requirements": covered_requirements,
            "uncovered_requirements": uncovered_requirements,
            "details": details,
        }

    @staticmethod
    def _build_test_case_text(
            test_case: Dict[str, Any],
    ) -> str:
        """
        Combines the meaningful fields of a test case into one
        searchable text representation.
        """

        title = str(test_case.get("title", ""))
        test_type = str(test_case.get("type", ""))
        priority = str(test_case.get("priority", ""))

        preconditions = " ".join(
            str(item)
            for item in test_case.get("preconditions", [])
        )

        steps = " ".join(
            str(item)
            for item in test_case.get("steps", [])
        )

        expected_result = str(
            test_case.get("expected_result", "")
        )

        return " ".join(
            [
                title,
                test_type,
                priority,
                preconditions,
                steps,
                expected_result,
            ]
        )

    @staticmethod
    def _requirement_match_score(
            requirement: str,
            test_case: Dict[str, Any],
    ) -> float:

        requirement_tokens = EvaluationService._normalize_tokens(
            requirement
        )

        if not requirement_tokens:
            return 0.0

        title = str(
            test_case.get("title", "")
        )

        steps = " ".join(
            str(step)
            for step in test_case.get("steps", [])
        )

        expected_result = str(
            test_case.get("expected_result", "")
        )

        preconditions = " ".join(
            str(item)
            for item in test_case.get(
                "preconditions",
                [],
            )
        )

        title_tokens = EvaluationService._normalize_tokens(
            title
        )

        step_tokens = EvaluationService._normalize_tokens(
            steps
        )

        expected_tokens = EvaluationService._normalize_tokens(
            expected_result
        )

        precondition_tokens = EvaluationService._normalize_tokens(
            preconditions
        )

        def coverage(tokens: Set[str]) -> float:
            if not requirement_tokens:
                return 0.0

            return (
                    len(requirement_tokens & tokens)
                    / len(requirement_tokens)
            )

        # Ana test case alanları.
        # Title ve steps daha yüksek öneme sahip.
        title_score = coverage(title_tokens)
        steps_score = coverage(step_tokens)
        expected_score = coverage(expected_tokens)
        precondition_score = coverage(
            precondition_tokens
        )

        text_score = (
                title_score * 0.35
                + steps_score * 0.30
                + expected_score * 0.25
                + precondition_score * 0.10
        )

        all_case_tokens = (
                title_tokens
                | step_tokens
                | expected_tokens
                | precondition_tokens
        )

        overall_text_coverage = coverage(
            all_case_tokens
        )

        # Source reference'lar RAG tarafından requirement'a
        # doğrudan bağlanmış olabilir. Bunları güçlü kanıt
        # olarak kullanıyoruz.
        source_score = 0.0

        source_references = test_case.get(
            "source_references",
            [],
        )

        if isinstance(source_references, list):
            for source in source_references:
                if not isinstance(source, dict):
                    continue

                quote = str(
                    source.get("quote", "")
                ).strip()

                if not quote:
                    continue

                quote_tokens = (
                    EvaluationService._normalize_tokens(
                        quote
                    )
                )

                if not quote_tokens:
                    continue

                source_overlap = (
                        len(
                            requirement_tokens
                            & quote_tokens
                        )
                        / len(requirement_tokens)
                )

                reverse_overlap = (
                        len(
                            requirement_tokens
                            & quote_tokens
                        )
                        / len(quote_tokens)
                )

                current_source_score = (
                        source_overlap * 0.70
                        + reverse_overlap * 0.30
                )

                source_score = max(
                    source_score,
                    current_source_score,
                )

        # Source requirement'ı neredeyse birebir gösteriyorsa,
        # bu en güçlü coverage kanıtıdır.
        if source_score >= 0.90:
            score = (
                    source_score * 0.70
                    + overall_text_coverage * 0.30
            )

            # Doğrudan source eşleşmesinde minimum güven.
            score = max(score, 0.85)

        else:
            # Source zayıf/yoksa test case'in gerçek içeriğine
            # daha fazla ağırlık ver.
            score = (
                    text_score * 0.55
                    + overall_text_coverage * 0.30
                    + source_score * 0.15
            )

        requirement_lower = requirement.lower()

        case_text = " ".join(
            [
                title,
                steps,
                expected_result,
                preconditions,
            ]
        ).lower()

        # Sayısal constraint varsa sayı source'ta veya
        # test case'in kendisinde bulunmalı.
        requirement_numbers = set(
            re.findall(
                r"\d+",
                requirement_lower,
            )
        )

        case_numbers = set(
            re.findall(
                r"\d+",
                case_text,
            )
        )

        source_numbers: Set[str] = set()

        if isinstance(source_references, list):
            for source in source_references:
                if not isinstance(source, dict):
                    continue

                quote = str(
                    source.get("quote", "")
                )

                source_numbers.update(
                    re.findall(
                        r"\d+",
                        quote.lower(),
                    )
                )

        if requirement_numbers:
            numbers_found = (
                    requirement_numbers.issubset(
                        case_numbers
                    )
                    or requirement_numbers.issubset(
                source_numbers
            )
            )

            if numbers_found:
                score += 0.05
            else:
                score -= 0.20

        return max(
            0.0,
            min(score, 1.0),
        )

    @staticmethod
    def _normalize_tokens(
            text: str,
    ) -> Set[str]:

        normalized_text = str(text).lower()

        replacements = {
            "sign-in": "login",
            "sign in": "login",
            "log in": "login",

            "authenticated": "authentication",
            "authenticate": "authentication",

            "credentials": "credential",

            "incorrect": "invalid",
            "wrong": "invalid",

            "addresses": "address",
            "emails": "email",
            "usernames": "username",
            "passwords": "password",

            "registered": "register",
            "registration": "register",
            "registering": "register",

            "rejected": "reject",
            "rejects": "reject",
            "rejecting": "reject",

            "displayed": "display",
            "displays": "display",
            "displaying": "display",

            "created": "create",
            "creates": "create",
            "creating": "create",

            "characters": "character",
            "fields": "field",
            "messages": "message",
            "requirements": "requirement",
            "matches": "match",
            "matching": "match",
        }

        for source, target in replacements.items():
            normalized_text = normalized_text.replace(
                source,
                target,
            )

        tokens = re.findall(
            r"[a-z0-9]+",
            normalized_text,
        )

        stop_words = {
            "the",
            "a",
            "an",
            "and",
            "or",
            "to",
            "of",
            "for",
            "in",
            "on",
            "with",
            "is",
            "are",
            "be",
            "been",
            "being",
            "must",
            "should",
            "this",
            "that",
            "it",
            "user",
            "system",
            "feature",
        }

        return {
            token
            for token in tokens
            if token not in stop_words
               and len(token) > 1
        }

    @staticmethod
    def _get_recommendation(
            overall_score: float,
            coverage_score: float,
            completeness_score: float,
            groundedness_score: float,
            uniqueness_score: float,
            specificity_score: float,
            duplicate_count: int,
    ) -> str:
        """
        Determines the overall quality recommendation based on
        multiple evaluation metrics instead of relying solely
        on the overall score.
        """

        if (
                duplicate_count > 0
                or coverage_score < 40
                or completeness_score < 60
                or groundedness_score < 60
                or uniqueness_score < 70
                or specificity_score < 60
        ):
            return "Poor - Regeneration recommended"

        if (
                overall_score >= 85
                and coverage_score >= 80
                and completeness_score >= 90
                and groundedness_score >= 90
                and uniqueness_score >= 95
                and specificity_score >= 90
                and duplicate_count == 0
        ):
            return "Excellent - Ready for review"

        if (
                overall_score >= 70
                and coverage_score >= 60
                and completeness_score >= 80
                and groundedness_score >= 80
                and uniqueness_score >= 85
                and specificity_score >= 75
                and duplicate_count == 0
        ):
            return "Good - Minor improvements suggested"

        if (
                overall_score >= 50
                and completeness_score >= 60
                and groundedness_score >= 60
        ):
            return "Fair - Manual review required"

        return "Poor - Regeneration recommended"