# TestPilot Lite RAG

**AI Test Scenario Generator using Retrieval-Augmented Generation (RAG)**

A professional-grade software testing tool that automatically generates structured test cases from project documentation using advanced AI and vector-based semantic search.

## Problem Statement

Writing comprehensive test cases is time-consuming and error-prone. Teams often struggle to:
- Create consistent test scenarios across multiple features
- Track test case coverage from requirements
- Maintain test documentation in sync with code
- Generate edge-case and security test scenarios systematically

## Solution

TestPilot Lite RAG solves this by:
1. **Indexing** project documents (user stories, API specs, acceptance criteria) using vector embeddings
2. **Retrieving** relevant context when you want to generate tests for a feature
3. **Generating** structured, grounded test cases automatically
4. **Exporting** in multiple formats (JSON, CSV, Markdown, Gherkin/BDD)
5. **Evaluating** quality metrics for generated tests

## Key Features

✅ **Document Management**
- Upload and manage project documentation (TXT, MD, JSON, YAML)
- Automatic chunking and semantic indexing
- Track document metadata and references

✅ **RAG Pipeline**
- Semantic retrieval using sentence-transformers embeddings
- ChromaDB vector store for efficient similarity search
- Context-aware test generation

✅ **Test Case Generation**
- Multiple test types: Positive, Negative, Edge Case, Validation, Security
- Structured JSON output with all test metadata
- Source document tracking and traceability

✅ **Export Formats**
- JSON (machine-readable)
- CSV (spreadsheet)
- Markdown (documentation)
- Gherkin (BDD/Cucumber)

✅ **Quality Evaluation**
- Coverage score
- Completeness metrics
- Groundedness (source reference) tracking
- Issue detection and recommendations

## Architecture

```
User Document Upload
         ↓
    Document Storage (SQLite)
         ↓
    Chunking Service
         ↓
    Embedding Generation (sentence-transformers)
         ↓
    Vector Store (ChromaDB)
         ↓
    [RAG Query]
         ↓
    Retrieval Service (similarity search)
         ↓
    Context + Feature Description
         ↓
    Test Case Generator
         ↓
    Evaluation Service (quality metrics)
         ↓
    Export Service (JSON/CSV/MD/Gherkin)
```

## Tech Stack

**Backend:**
- FastAPI (Python web framework)
- SQLAlchemy (ORM)
- SQLite (metadata storage)
- sentence-transformers (embeddings)
- ChromaDB (vector database)

**Frontend:**
- React 18 + TypeScript
- Vite (build tool)
- CSS3 (dark theme UI)

**Architecture:**
- Modular service layer
- Clean separation of concerns
- Provider-agnostic LLM adapter (ready for OpenAI, Azure, Ollama, Foundry Local)

## Project Structure

```
testpilot-lite-rag/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   ├── health.py
│   │   │   ├── documents.py
│   │   │   └── generation.py
│   │   ├── services/
│   │   │   ├── document_service.py
│   │   │   ├── chunking_service.py
│   │   │   ├── embedding_service.py
│   │   │   ├── vector_store.py
│   │   │   ├── rag_service.py
│   │   │   ├── generation_service.py
│   │   │   └── evaluation_service.py
│   │   ├── models/
│   │   │   └── document.py
│   │   ├── db/
│   │   │   ├── models.py
│   │   │   └── database.py
│   │   ├── main.py
│   │   └── config.py
│   ├── requirements.txt
│   └── README.md
├── frontend/
│   ├── src/
│   │   ├── pages/
│   │   │   ├── Dashboard.tsx
│   │   │   ├── Documents.tsx
│   │   │   ├── GenerateTests.tsx
│   │   │   ├── Results.tsx
│   │   │   └── History.tsx
│   │   ├── components/
│   │   ├── api/
│   │   │   └── apiClient.ts
│   │   ├── App.tsx
│   │   ├── App.css
│   │   └── main.tsx
│   ├── package.json
│   ├── tsconfig.json
│   ├── vite.config.ts
│   └── README.md
├── samples/
│   ├── auth_user_stories.md
│   └── auth_api.yaml
└── README.md
```

## Getting Started

### Backend Setup

```bash
cd backend
pip install -r requirements.txt
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Backend will be available at `http://localhost:8000`
- API docs: `http://localhost:8000/docs`

### Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

Frontend will be available at `http://localhost:5173`

## Usage Workflow

### 1. Upload Documents
- Go to **Documents** page
- Upload user stories, API specs, or acceptance criteria
- System automatically chunks and indexes them

### 2. Generate Test Cases
- Go to **Generate Tests** page
- Select feature/module
- Choose test types (Positive, Negative, Edge Case, etc.)
- Describe what you want to test
- Click **Generate Test Cases**

### 3. Review & Export
- View structured test cases with source references
- Check quality evaluation metrics
- Export in your preferred format:
  - JSON for integration with test frameworks
  - CSV for spreadsheet analysis
  - Markdown for documentation
  - Gherkin for BDD/Cucumber

## Demo Scenario

Sample authentication module documentation is included:
- `samples/auth_user_stories.md` - User stories for login, registration, password reset
- `samples/auth_api.yaml` - API specification

To test:
1. Upload `auth_user_stories.md` 
2. Query: "Generate tests for login functionality"
3. Receive structured test cases for positive, negative, edge cases

## Metrics & Evaluation

Each generation includes quality metrics:
- **Coverage Score**: Overall test coverage quality
- **Completeness Score**: All required fields present
- **Groundedness Score**: Test cases backed by source documents
- **Issue Detection**: Missing steps, duplicate cases, references

## Future Enhancements

- [ ] PDF document support
- [ ] Azure AI Foundry integration
- [ ] Ollama/local LLM support
- [ ] Jira integration (auto-upload from tickets)
- [ ] Playwright/Cypress code generation
- [ ] Requirement traceability matrix
- [ ] Multi-user workspaces
- [ ] Test case versioning and history
- [ ] Collaboration & comments
- [ ] Custom test case templates

## Performance Notes

- Chunking: ~1-2s per document (depends on size)
- Embedding generation: First model load ~10s, then ~100ms per query
- Vector search: <100ms for typical queries
- Test generation: ~500ms for 5 test cases

## Security Considerations

- No data is sent to external LLM services by default
- Local embedding model (sentence-transformers)
- ChromaDB stores data locally
- CORS enabled for development (configure for production)

## Contributing

This is a Microsoft Summer Certificate project demonstrating:
- RAG architecture and implementation
- Vector databases and semantic search
- Test generation automation
- FastAPI backend design
- React frontend development
- Professional software engineering practices

## License

Microsoft Summer Certificate Project - 2026

---

**Built with ❤️ using FastAPI, React, ChromaDB, and sentence-transformers**
