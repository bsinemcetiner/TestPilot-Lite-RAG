import json
from typing import List, Dict, Any, Tuple

from pydantic import ValidationError
from app.services.llm_service import LLMService
from app.schemas.test_case import TestCaseSchema
import re


class TestCaseGenerator:
    @staticmethod
    def generate_test_cases(
        feature_name: str,
        query: str,
        retrieved_context: List[Dict[str, Any]],
        test_types: List[str] = None,
        num_cases: int = 5,
        provider_name: str = 'mock'
    ) -> Tuple[List[Dict[str, Any]], str]:
        """
        Generate structured test cases based on feature name and retrieved context.
        Uses an LLM provider backend and validates with Pydantic schema.
        Fills any gap between generated and requested count with category-distributed fallbacks.
        """

        
        if test_types is None:
            test_types = ["Positive", "Negative", "Edge Case"]

        try:
            raw_cases, used_provider = LLMService.generate_test_cases(
                feature_name=feature_name,
                query=query,
                retrieved_context=retrieved_context,
                test_types=test_types,
                num_cases=num_cases,
                provider_name=provider_name,
            )
        except Exception as exc:
            print(
                f"LLM generation failed: "
                f"{type(exc).__name__}: {exc}"
            )
            raw_cases = []
            used_provider = "mock_fallback"

        if not isinstance(raw_cases, list):
            raw_cases = []

        validated_cases = []

        for idx, case in enumerate(raw_cases or [], 1):
            case["id"] = idx

            try:
                validated = TestCaseSchema(**case)
                validated_cases.append(validated.dict())

            except ValidationError as e:
                print(f"Validation failed for case {idx}: {e}")
                continue

        validated_cases = (
            TestCaseGenerator._remove_duplicate_cases(
                validated_cases
            )
        )



        # Fill gap: if we have fewer cases than requested, add category-distributed fallbacks
        # gap_filled_count = 0
        #if len(validated_cases) < num_cases:
        #    missing_count = num_cases - len(validated_cases)
        #    fallback_cases = TestCaseGenerator._create_distributed_fallback_cases(
        #        feature_name=feature_name,
        #        query=query,
        #       retrieved_context=retrieved_context,
        #        test_types=test_types,
        #        count=missing_count,
        #        start_index=len(validated_cases) + 1,
        #        used_types=[case.get('type', 'Positive') for case in validated_cases],
        #    )
        #    gap_filled_count = len(fallback_cases)
        #    validated_cases.extend(fallback_cases)



        # Re-index and update titles with final IDs
        for index, test_case in enumerate(
                validated_cases,
                start=1,
        ):
            test_case["id"] = index
            # Update title to reflect final case number
            if " - Case " in test_case.get("title", ""):
                parts = test_case["title"].rsplit(" - Case ", 1)
                test_case["title"] = f"{parts[0]} - Case {index}"

        if not validated_cases:
            raise ValueError(
                "LLM returned no valid test cases after schema validation."
            )

        return validated_cases, used_provider

    @staticmethod
    def _remove_duplicate_cases(
            test_cases: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """
        Aynı veya neredeyse aynı adımlara ve beklenen sonuca
        sahip test case'leri kaldırır.
        """
        unique_cases: List[Dict[str, Any]] = []
        signatures: set[str] = set()

        for test_case in test_cases:
            steps = " ".join(
                str(step)
                for step in test_case.get(
                    "steps",
                    [],
                )
            )

            expected = str(
                test_case.get(
                    "expected_result",
                    "",
                )
            )

            test_type = str(
                test_case.get(
                    "type",
                    "",
                )
            )

            raw_signature = (
                f"{steps}|{expected}"
            ).lower()

            signature = re.sub(
                r"[^a-z0-9]+",
                " ",
                raw_signature,
            ).strip()

            if signature in signatures:
                continue

            signatures.add(signature)
            unique_cases.append(test_case)

        return unique_cases

    @staticmethod
    def _build_fallback_case(
        feature_name: str,
        test_type: str,
        index: int,
        retrieved_context: List[Dict[str, Any]],
        query: str = "",
    ) -> Dict[str, Any]:
        """Build a context-aware fallback test case."""
        # Extract key words from query and context for specificity
        context_snippet = ""
        if retrieved_context and len(retrieved_context) > 0:
            context_snippet = retrieved_context[0]['text'][:100]
        
        # Create type-specific steps
        steps = []
        if test_type == "Positive":
            steps = [
                f"Navigate to {feature_name} module",
                f"Provide valid input based on requirements: {context_snippet[:50]}",
                f"Submit the action",
            ]
            expected = f"The system successfully processes the request for {feature_name}."
        elif test_type == "Negative":
            steps = [
                f"Navigate to {feature_name} module",
                f"Provide invalid or boundary input",
                f"Attempt to submit",
            ]
            expected = f"The system properly rejects invalid input for {feature_name}."
        elif test_type == "Edge Case":
            steps = [
                f"Navigate to {feature_name} module",
                f"Provide edge case input (boundary values, special characters)",
                f"Verify handling of edge conditions",
            ]
            expected = f"The system handles edge cases gracefully for {feature_name}."
        elif test_type == "Validation":
            steps = [
                f"Navigate to {feature_name} module",
                f"Attempt to input data that violates validation rules",
                f"Check validation error messages",
            ]
            expected = f"Proper validation errors are displayed for {feature_name}."
        elif test_type == "Security":
            steps = [
                f"Navigate to {feature_name} module",
                f"Attempt to bypass security controls",
                f"Verify security measures are in place",
            ]
            expected = f"Security controls for {feature_name} are properly enforced."
        else:
            steps = [
                f"Access {feature_name} functionality",
                f"Perform {test_type.lower()} scenario",
                f"Verify result",
            ]
            expected = f"The system correctly handles {test_type.lower()} for {feature_name}."

        return {
            'id': index,
            'title': f'{test_type}: {feature_name} - Case {index}',
            'type': test_type if test_type in ['Positive', 'Negative', 'Edge Case', 'Validation', 'Security'] else 'Positive',
            'priority': 'High' if test_type in ['Positive', 'Security'] else 'Medium',
            'preconditions': [
                f'{feature_name} is accessible',
                f'User has necessary permissions'
            ],
            'steps': steps,
            'expected_result': expected,
            'source_references': [
                {
                    'document_name': c['metadata'].get('document_name', 'Unknown'),
                    'chunk_id': c['metadata'].get('chunk_id', f'chunk_{i}'),
                    'quote': c['text'][:120]
                }
                for i, c in enumerate(retrieved_context[:2], start=1)
            ],
            'confidence': 0.6,
        }

    @staticmethod
    def _create_distributed_fallback_cases(
        feature_name: str,
        query: str,
        retrieved_context: List[Dict[str, Any]],
        test_types: List[str],
        count: int,
        start_index: int,
        used_types: List[str],
    ) -> List[Dict[str, Any]]:
        """Create multiple fallback cases with distributed test types."""
        fallback_cases = []
        
        # Calculate which types to prioritize
        remaining_types = [t for t in test_types if t in ['Positive', 'Negative', 'Edge Case', 'Validation', 'Security']]
        if not remaining_types:
            remaining_types = ['Positive', 'Negative', 'Edge Case']
        
        # Distribute types across fallback cases
        type_index = 0
        for i in range(count):
            selected_type = remaining_types[type_index % len(remaining_types)]
            type_index += 1
            
            case = TestCaseGenerator._build_fallback_case(
                feature_name=feature_name,
                test_type=selected_type,
                index=start_index + i,
                retrieved_context=retrieved_context,
                query=query,
            )
            fallback_cases.append(case)
        
        return fallback_cases

    @staticmethod
    def to_gherkin(test_case: Dict[str, Any]) -> str:
        """Convert test case to Gherkin format."""
        title = test_case['title']
        preconditions = test_case['preconditions']
        steps = test_case['steps']
        expected = test_case['expected_result']
        
        gherkin = f"Scenario: {title}\n"
        
        for precond in preconditions:
            gherkin += f"  Given {precond}\n"
        
        for i, step in enumerate(steps):
            if i == 0:
                gherkin += f"  When {step}\n"
            elif i == len(steps) - 1:
                gherkin += f"  Then {step}\n"
            else:
                gherkin += f"  And {step}\n"
        
        gherkin += f"  Then {expected}\n"
        
        return gherkin

    @staticmethod
    def to_markdown(test_cases: List[Dict[str, Any]]) -> str:
        """Export test cases to Markdown."""
        md = "# Test Cases\n\n"
        
        for tc in test_cases:
            md += f"## {tc['title']}\n\n"
            md += f"**Type:** {tc['type']}\n"
            md += f"**Priority:** {tc['priority']}\n\n"
            
            md += "**Preconditions:**\n"
            for pre in tc['preconditions']:
                md += f"- {pre}\n"
            
            md += "\n**Steps:**\n"
            for i, step in enumerate(tc['steps'], 1):
                md += f"{i}. {step}\n"
            
            md += f"\n**Expected Result:** {tc['expected_result']}\n\n"
            
            if tc.get('source_references'):
                source_strings = [
                    f"{src.get('document_name', 'Unknown')} ({src.get('chunk_id', '')}) - {src.get('quote', '')}".strip(' -')
                    for src in tc['source_references']
                ]
                md += f"**Source:** {', '.join(source_strings)}\n\n"
            
            md += "---\n\n"
        
        return md

    @staticmethod
    def to_csv(test_cases: List[Dict[str, Any]]) -> str:
        """Export test cases to CSV."""
        import csv
        import io
        
        output = io.StringIO()
        writer = csv.writer(output)
        
        writer.writerow(['Test ID', 'Title', 'Type', 'Priority', 'Preconditions', 'Steps', 'Expected Result', 'Sources'])
        
        for tc in test_cases:
            source_strings = [
                f"{src.get('document_name', 'Unknown')} ({src.get('chunk_id', '')}) - {src.get('quote', '')}".strip(' -')
                for src in tc.get('source_references', [])
            ]
            writer.writerow([
                tc['id'],
                tc['title'],
                tc['type'],
                tc['priority'],
                '; '.join(tc['preconditions']),
                '; '.join(tc['steps']),
                tc['expected_result'],
                '; '.join(source_strings)
            ])
        
        return output.getvalue()

    @staticmethod
    def to_json(test_cases: List[Dict[str, Any]]) -> str:
        """Export test cases to JSON."""
        return json.dumps(test_cases, indent=2)
