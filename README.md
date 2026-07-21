# TestPilot Lite RAG

AI-powered software test case generation using Retrieval-Augmented Generation (RAG).

TestPilot Lite RAG is a full-stack application that automatically generates structured software test cases from project documentation. By combining semantic search with Large Language Models (LLMs), the system retrieves relevant requirements and produces grounded, traceable, and exportable test scenarios.

---

## Features

### Intelligent Document Processing

- Upload project documents (TXT, Markdown, JSON, YAML)
- Automatic document chunking
- Semantic embedding generation
- Metadata management

### Retrieval-Augmented Generation (RAG)

- Vector-based semantic search
- Context-aware requirement retrieval
- ChromaDB vector database
- Sentence Transformers embeddings

### AI Test Case Generation

Generate multiple categories of software test cases:

- Positive Tests
- Negative Tests
- Edge Cases
- Validation Tests
- Security Tests

Each generated test case includes:

- Title
- Priority
- Preconditions
- Test Steps
- Expected Result
- Source References

### Quality Evaluation

Every generation is automatically evaluated using:

- Coverage Score
- Completeness Score
- Groundedness Score
- Recommendations

### Export Options

Generated test cases can be exported as:

- JSON
- CSV
- Markdown
- Gherkin (BDD)

---

## System Architecture

```
                Project Documents
                        │
                        ▼
               Document Processing
                        │
                        ▼
              Chunking & Embeddings
                        │
                        ▼
                 ChromaDB Vector Store
                        │
                        ▼
                 Semantic Retrieval
                        │
                        ▼
          Context + User Query + LLM
                        │
                        ▼
          Structured Test Case Output
                        │
                        ▼
          Quality Evaluation & Export
```

---

## Tech Stack

### Backend

- FastAPI
- SQLAlchemy
- SQLite
- ChromaDB
- Sentence Transformers

### Frontend

- React 18
- TypeScript
- Vite

### AI

- Retrieval-Augmented Generation (RAG)
- Vector Embeddings
- Provider-agnostic LLM Layer
- OpenAI
- Azure OpenAI
- Ollama
- Azure AI Foundry (ready)

---

## Project Structure

```
testpilot-lite-rag
│
├── backend
│   ├── api
│   ├── services
│   ├── models
│   ├── db
│   └── app
│
├── frontend
│   ├── components
│   ├── pages
│   └── api
│
├── samples
│
└── README.md
```

---

## Getting Started

### Backend

```bash
cd backend

pip install -r requirements.txt

uvicorn app.main:app --reload
```

Backend:

```
http://localhost:8000
```

Swagger:

```
http://localhost:8000/docs
```

---

### Frontend

```bash
cd frontend

npm install

npm run dev
```

Frontend:

```
http://localhost:5173
```

---

## Usage

1. Upload project documents.
2. The system automatically chunks and indexes them.
3. Enter a feature or requirement.
4. Generate AI-powered test cases.
5. Review evaluation metrics.
6. Export results in the desired format.

---

## Example Output

```json
{
  "title": "Login with valid credentials",
  "priority": "High",
  "preconditions": ["User account exists"],
  "steps": [
    "Navigate to Login page",
    "Enter valid username",
    "Enter valid password",
    "Click Login"
  ],
  "expected_result": "User is redirected to Dashboard"
}
```

---

## Evaluation Metrics

The system automatically evaluates generated test cases using:

| Metric       | Description                                                           |
| ------------ | --------------------------------------------------------------------- |
| Coverage     | Measures how many requirements are covered                            |
| Completeness | Checks whether required test fields exist                             |
| Groundedness | Measures whether generated tests are supported by retrieved documents |

---

## Future Improvements

- PDF support
- Jira integration
- Playwright test generation
- Cypress test generation
- Requirement traceability matrix
- Version history
- Multi-user workspace
- Azure AI Foundry deployment

---

## Why This Project?

This project was developed as part of the **Microsoft Summer Certificate Program (2026)**.

It demonstrates practical implementation of:

- Retrieval-Augmented Generation (RAG)
- Semantic Search
- Vector Databases
- AI-assisted Software Testing
- FastAPI Backend Development
- React Frontend Development
- Modular Software Architecture

---

## License

This repository was created for educational and portfolio purposes as part of the Microsoft Summer Certificate Program.
