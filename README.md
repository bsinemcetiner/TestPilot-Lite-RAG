# TestPilot Lite RAG

Documentation-driven AI test case generation using **Retrieval-Augmented Generation (RAG)**.

TestPilot Lite RAG is a full-stack application that automatically generates structured software test cases from project documentation.

The system retrieves relevant requirements from an indexed knowledge base, generates grounded test scenarios using Large Language Models (LLMs), evaluates their quality and allows users to review, manage and export the generated results through a modern web interface.

---

## Highlights

- Upload software requirements and project documentation (TXT, MD)
- Text-based PDF extraction support (OCR is not supported)
- Basic JSON/YAML file upload (treated as flat text for retrieval; full OpenAPI structural parsing is not yet supported)
- Semantic retrieval using ChromaDB and Sentence Transformers
- AI-powered software test generation (Ollama as main provider, Mock as fallback)
- Automatic quality evaluation (Coverage, Completeness, Groundedness, Uniqueness, Specificity)
- Generation history persisted in backend SQLite database
- Export generated test cases
- Modern React + TypeScript dashboard

---

## Dashboard

Monitor indexed documents, retrieval readiness and workspace status from a single dashboard.

<p align="center">
  <img src="docs/images/dashboard.png" width="50%">
</p>

## Document Management

Upload project documentation using drag-and-drop or paste requirements directly into the knowledge base.

<p align="center">
  <img src="docs/images/documents.png" width="50%">
</p>

## AI Test Generation

Generate structured software test cases by selecting a feature, choosing scenario categories and configuring the generation settings.

<p align="center">
  <img src="docs/images/generate-tests.png" width="50%">
</p>

## Generated Results

Review generated test cases, source references, evaluation metrics and export the generated output.

<p align="center">
<img src="docs/images/results.png" width="50%">
</p>

## Generation History

Browse previous generations, search records, mark favorites and reopen saved results.

<p align="center">
<img src="docs/images/history.png" width="50%">
</p>

---

# Features

- Upload and index project documentation
- Text-based PDF extraction
- Semantic retrieval using ChromaDB
- AI-powered test case generation
- Multiple test categories
- Automatic quality evaluation with 5 key metrics
- Generation history persisted in backend SQLite database
- Export to JSON, CSV, Markdown and Gherkin

# Workflow

```mermaid
flowchart LR
A[Project Documents] --> B[Indexing]
B --> C[Semantic Retrieval]
C --> D[LLM]
D --> E[Test Cases]
E --> F[Evaluation]
E --> G[Export]
```

---

# Technology Stack

| Layer        | Technologies                                                                                                                  |
| ------------ | ----------------------------------------------------------------------------------------------------------------------------- |
| **Backend**  | FastAPI, SQLAlchemy, SQLite                                                                                                   |
| **Frontend** | React 18, TypeScript, Vite, Lucide React, CSS3                                                                                |
| **AI / RAG** | ChromaDB, Sentence Transformers, Retrieval-Augmented Generation (RAG), Ollama (Tested/Working Main), Mock (Fallback/Test), OpenAI/Azure OpenAI (Experimental/Unverified), Azure AI Foundry (Planned) |
| **Storage**  | SQLite, ChromaDB, Browser Local Storage                                                                                       |

# Installation

## Backend

```bash
cd backend

pip install -r requirements.txt

uvicorn app.main:app --reload
```

Backend

```
http://localhost:8000
```

Swagger

```
http://localhost:8000/docs
```

---

## Frontend

```bash
cd frontend

npm install

npm install lucide-react

npm run dev
```

Frontend

```
http://localhost:5173
```

---

# Usage

1. Upload project documentation.
2. Index the uploaded files.
3. Generate AI-powered test cases.
4. Review quality evaluation metrics.
5. Browse generation history and export the generated output.

---

# Evaluation Metrics

| Metric       | Description                                                                   |
| ------------ | ----------------------------------------------------------------------------- |
| Coverage     | Percentage of requirements addressed by generated test cases                  |
| Completeness | Measures whether generated test cases contain all required fields             |
| Groundedness | Indicates whether generated scenarios are supported by retrieved requirements |
| Uniqueness   | Evaluates the diversity of the test cases and penalizes duplicates            |
| Specificity  | Checks if the generated test steps are specific and non-generic               |

---

# Future Improvements

- Full OpenAPI structural parsing for test generation
- Jira integration
- Playwright test generation
- Cypress test generation
- Requirement Traceability Matrix (RTM)
- Docker deployment
- CI/CD pipeline
- Multi-user workspace
- Authentication
- Azure AI Foundry deployment

---

# Why This Project?

TestPilot Lite RAG was developed as part of the **Microsoft Summer Certificate Program (2026)**.

The project demonstrates practical implementation of:

- Retrieval-Augmented Generation (RAG)
- Semantic Search
- Vector Databases
- AI-assisted Software Testing
- FastAPI Backend Development
- React + TypeScript Frontend
- Modern UI/UX Design
- Modular Software Architecture

---

# Authors

- **Betül Sinem Çetiner**
- **Yağız Zorlu**

GitHub:

- https://github.com/bsinemcetiner
- https://github.com/Yagizzorlu
