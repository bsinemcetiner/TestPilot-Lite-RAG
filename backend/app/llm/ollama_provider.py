import os
import re
import json
from typing import List, Dict, Any

try:
    import requests
except ImportError:
    requests = None

from app.llm.base_provider import LLMProvider


class OllamaProvider(LLMProvider):
    name = 'ollama'

    def __init__(self):
        if requests is None:
            raise ImportError('requests package is not installed')

        self.base_url = os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434')
        self.model = os.getenv('OLLAMA_MODEL', 'llama2')

    def generate_test_cases(
        self,
        feature_name: str,
        query: str,
        retrieved_context: List[Dict[str, Any]],
        test_types: List[str],
        num_cases: int,
    ) -> List[Dict[str, Any]]:
        context_text = '\n\n'.join(
            [f"[{i+1}] {item['metadata'].get('document_name', 'Unknown')}: {item['text']}" for i, item in enumerate(retrieved_context)]
        )

        test_types_str = ', '.join(test_types) if test_types else 'Positive, Negative, Edge Case'
        
        prompt = (
            f"You are a test generation assistant that creates tests EXCLUSIVELY from provided requirements.\n\n"
            f"TASK: Generate EXACTLY {num_cases} test cases for '{feature_name}'\n\n"
            f"CRITICAL RULE - SOURCE-GROUNDED GENERATION:\n"
            f"- Each test case MUST be derived ONLY from the actual requirements in the retrieved context below\n"
            f"- Do NOT invent behaviors, edge cases, or security scenarios NOT explicitly mentioned in the context\n"
            f"- Do NOT use generic terms like 'perform action', 'verify result', 'handle gracefully'\n"
            f"- The 'steps' array MUST contain AT LEAST 3 concrete steps. 1 or 2 steps are NOT accepted.\n"
            f"- Do NOT generate generic filler steps; every single step MUST be specific to the requirements.\n"
            f"- Each step MUST directly reference or quote a specific requirement from the context\n"
            f"- Each expected_result MUST be stated or implied in the requirements\n"
            f"- If a test type (Positive/Negative/Edge Case) lacks explicit requirement data, use only what IS documented\n\n"
            f"TEST DISTRIBUTION:\n"
            f"- Return EXACTLY {num_cases} test cases (no more, no less)\n"
            f"- Distribute across: {test_types_str}\n"
            f"- Each case type must have a basis in the retrieved context\n\n"
            f"RETRIEVED REQUIREMENTS (source of truth - use ONLY these):\n"
            f"{context_text}\n\n"
            f"USER QUERY (context for test focus):\n{query}\n\n"
            f"OUTPUT FORMAT - Return EXACTLY {num_cases} JSON objects in an array:\n\n"
            f"Each test case MUST have this structure:\n"
            f"{{\n"
            f'  "title": "test name based on actual requirement",\n'
            f'  "type": "Positive" (or one of: {test_types_str}),\n'
            f'  "priority": "High",\n'
            f'  "preconditions": ["precondition 1", "precondition 2"],\n'
            f'  "steps": ["action 1", "action 2", "action 3"],\n'
            f'  "expected_result": "outcome from requirements",\n'
            f'  "source_references": [\n'
            f'    {{\n'
            f'      "document_name": "Exact document name",\n'
            f'      "chunk_id": "Chunk identifier",\n'
            f'      "quote": "Exact supporting text from context"\n'
            f'    }}\n'
            f'  ],\n'
            f'  "confidence": 0.9\n'
            f"}}\n\n"
            f"IMPORTANT:\n"
            f"- source_references is a LIST of objects, not strings\n"
            f"- Each object must have: document_name (string), chunk_id (string), quote (string)\n"
            f"- Include at least one source_reference with exact quote from requirements\n"
            f"- confidence: use 0.8-1.0 if fully grounded in context\n\n"
            f"Return ONLY a valid JSON array of exactly {num_cases} objects. No explanation text outside the JSON."
        )

        url = f"{self.base_url}/api/generate"
        response = requests.post(url, json={
            'model': self.model,
            'prompt': prompt,
            'stream': False,
            'format': 'json',
        })
        response.raise_for_status()

        data = response.json()
        text = data.get('response', '')
        test_cases = self._parse_response(text, num_cases, retrieved_context)
        return test_cases

    def _parse_response(self, text: str, num_cases: int, retrieved_context: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Parse Ollama response which may contain JSON with optional markdown wrapping.
        Try direct parsing first, then fallback to markdown/regex extraction.
        Normalizes source_references format if needed.
        """
        if not text or not isinstance(text, str):
            raise ValueError('Ollama provider returned empty or invalid response')

        original_text = text
        text = text.strip()

        # Strategy 1: Try direct JSON parsing first (handles valid JSON array/dict)
        try:
            data = json.loads(text)
            return self._process_parsed_data(data, num_cases, retrieved_context)
        except json.JSONDecodeError:
            pass  # Try next strategy

        # Strategy 2: Try markdown fence extraction if direct parse failed
        json_match = re.search(r'```(?:json)?\s*([\s\S]*?)```', text)
        if json_match:
            text = json_match.group(1).strip()
            try:
                data = json.loads(text)
                return self._process_parsed_data(data, num_cases, retrieved_context)
            except json.JSONDecodeError:
                pass  # Try next strategy

        # Strategy 3: Try JSON array regex extraction as last fallback
        json_array_match = re.search(r'\[\s*\{[\s\S]*?\}\s*\]', text)
        if json_array_match:
            text = json_array_match.group(0).strip()
            try:
                data = json.loads(text)
                return self._process_parsed_data(data, num_cases, retrieved_context)
            except json.JSONDecodeError:
                pass  # Fall through to error

        # All parsing strategies failed
        raise ValueError(f'Ollama provider returned invalid JSON response: {original_text[:200]}')

    def _process_parsed_data(self, data: Any, num_cases: int, retrieved_context: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Process successfully parsed JSON data (list or dict).
        Handles wrapper objects and normalizes source_references.
        """

        
        if isinstance(data, list):
            # Already an array of test cases
            normalized_cases = []
            for case in data:
                if isinstance(case, dict):
                    case = self._normalize_source_references(case, retrieved_context)
                    normalized_cases.append(case)
            
            if len(normalized_cases) >= num_cases:
                return normalized_cases[:num_cases]
            elif len(normalized_cases) > 0:
                return normalized_cases
            else:
                raise ValueError('Ollama provider returned empty array')
        
        elif isinstance(data, dict):
            # Check for wrapper keys containing test cases array or string
            wrapper_keys = ['test_cases', 'tests', 'cases', 'response', 'output', 'results', 'testCases']
            
            for wrapper_key in wrapper_keys:
                if wrapper_key not in data:
                    continue
                
                value = data[wrapper_key]
                
                
                # If value is list, process as test cases
                if isinstance(value, list):

                    normalized_cases = []
                    for case in value:
                        if isinstance(case, dict):
                            case = self._normalize_source_references(case, retrieved_context)
                            normalized_cases.append(case)
                    
                    if len(normalized_cases) >= num_cases:
                        return normalized_cases[:num_cases]
                    elif len(normalized_cases) > 0:
                        return normalized_cases
                    else:
                        raise ValueError(f'Ollama wrapper "{wrapper_key}" contained empty array')
                
                # If value is string, try to parse as JSON
                elif isinstance(value, str):

                    try:
                        parsed_value = json.loads(value)
                        if isinstance(parsed_value, list):

                            normalized_cases = []
                            for case in parsed_value:
                                if isinstance(case, dict):
                                    case = self._normalize_source_references(case, retrieved_context)
                                    normalized_cases.append(case)
                            
                            if len(normalized_cases) >= num_cases:
                                return normalized_cases[:num_cases]
                            elif len(normalized_cases) > 0:
                                return normalized_cases
                        elif isinstance(parsed_value, dict):

                            parsed_value = self._normalize_source_references(parsed_value, retrieved_context)
                            return [parsed_value]
                    except json.JSONDecodeError:
                        pass  # Continue to next key
            
            # No wrapper key with array found
            # Check if dict itself is a test case (has title, type, steps, etc.)
            test_case_fields = {'title', 'type', 'priority', 'preconditions', 'steps', 'expected_result'}
            if any(field in data for field in test_case_fields):

                normalized = self._normalize_source_references(data, retrieved_context)
                return [normalized]
            else:

                raise ValueError(f"Ollama dict has no test_cases array or test case fields. Keys: {list(data.keys())}")
        
        else:
            raise ValueError(f'Ollama response must be JSON array or dict, got {type(data).__name__}')

    def _normalize_source_references(self, case: Dict[str, Any], retrieved_context: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Normalize source_references to proper format [{"document_name": str, "chunk_id": str, "quote": str}, ...]
        Also normalizes type, priority, and list fields to prevent Pydantic validation errors.
        """
        # Normalize enums (type and priority) to match Pydantic Literal exact casing
        if 'type' in case and isinstance(case['type'], str):
            t = case['type'].lower()
            if 'positive' in t: case['type'] = 'Positive'
            elif 'negative' in t: case['type'] = 'Negative'
            elif 'edge' in t: case['type'] = 'Edge Case'
            elif 'validation' in t: case['type'] = 'Validation'
            elif 'security' in t: case['type'] = 'Security'
            
        if 'priority' in case and isinstance(case['priority'], str):
            p = case['priority'].lower()
            if 'high' in p: case['priority'] = 'High'
            elif 'medium' in p: case['priority'] = 'Medium'
            elif 'low' in p: case['priority'] = 'Low'
            
        # Normalize list fields if they were output as a single string
        for field in ['steps', 'preconditions']:
            if field in case and isinstance(case[field], str):
                case[field] = [s.strip('- *1234567890.') for s in case[field].split('\n') if s.strip()]

        if 'source_references' not in case:
            # Add default source reference from context if missing
            if retrieved_context and len(retrieved_context) > 0:
                case['source_references'] = [
                    {
                        'document_name': retrieved_context[0]['metadata'].get('document_name', 'Unknown'),
                        'chunk_id': retrieved_context[0]['metadata'].get('chunk_id', 'unknown'),
                        'quote': retrieved_context[0]['text'][:100]
                    }
                ]
            else:
                case['source_references'] = []
            return case

        source_refs = case['source_references']
        
        # If already a list of dicts with correct structure, keep it
        if isinstance(source_refs, list) and len(source_refs) > 0:
            if isinstance(source_refs[0], dict) and 'document_name' in source_refs[0]:
                return case  # Already normalized
        
        # Try to recover if malformed (e.g., list of strings)
        if isinstance(source_refs, list) and len(retrieved_context) > 0:
            # Convert to proper dict format using context metadata
            normalized = []
            for i, ref in enumerate(source_refs[:1]):  # Use first context only
                normalized.append({
                    'document_name': retrieved_context[0]['metadata'].get('document_name', 'Unknown'),
                    'chunk_id': retrieved_context[0]['metadata'].get('chunk_id', 'unknown'),
                    'quote': str(ref)[:150] if ref else retrieved_context[0]['text'][:100]
                })
            case['source_references'] = normalized if normalized else [
                {
                    'document_name': retrieved_context[0]['metadata'].get('document_name', 'Unknown'),
                    'chunk_id': retrieved_context[0]['metadata'].get('chunk_id', 'unknown'),
                    'quote': retrieved_context[0]['text'][:100]
                }
            ]
        
        return case
