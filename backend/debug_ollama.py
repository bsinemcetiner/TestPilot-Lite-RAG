import sys
from app.services.generation_service import TestCaseGenerator
from app.services.rag_service import RAGService

def run():
    try:
        retrieved = RAGService.retrieve_context('Login', 5)
        for i in range(3):
            print(f"--- Attempt {i} ---")
            cases, prov = TestCaseGenerator.generate_test_cases(
                'Login Requirements', 
                'Login requirements', 
                retrieved, 
                ['Positive', 'Negative', 'Edge Case', 'Validation', 'Security'], 
                5, 
                'ollama'
            )
    except Exception as e:
        print('Error:', e)

if __name__ == '__main__':
    run()
