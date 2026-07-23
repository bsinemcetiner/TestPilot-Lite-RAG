import { useEffect, useState } from "react";
import {
  ArrowRight,
  CheckCircle2,
  Database,
  FileText,
  FlaskConical,
  Layers3,
  UploadCloud,
} from "lucide-react";

import { getDocuments, getChunkCount } from "../api/apiClient";

function Dashboard() {
  const [docCount, setDocCount] = useState(0);
  const [chunkCount, setChunkCount] = useState(0);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchStats = async () => {
      try {
        const docs = await getDocuments();
        setDocCount(docs.length);

        const chunkCounts = await Promise.all(
          docs.map((doc) => getChunkCount(doc.id)),
        );

        const totalChunks = chunkCounts.reduce(
          (total, count) => total + count,
          0,
        );

        setChunkCount(totalChunks);
      } catch (error) {
        console.error("Failed to fetch dashboard statistics", error);
      } finally {
        setLoading(false);
      }
    };

    fetchStats();
  }, []);

  return (
    <div className="page-stack">
      <header className="page-header dashboard-header">
        <div>
          <p className="eyebrow">Workspace Overview</p>
          <h1>Dashboard</h1>
          <p className="page-description">
            Review indexed documents, monitor retrieval readiness and manage the
            test generation workflow.
          </p>
        </div>

        <div className="header-status">
          <span className="status-dot" />
          Pipeline operational
        </div>
      </header>

      <section className="metrics-grid">
        <article className="metric-card">
          <div className="metric-card-header">
            <span className="metric-icon">
              <FileText size={20} />
            </span>
            <span className="metric-status">Indexed</span>
          </div>

          <div className="metric-value">
            {loading ? <span className="skeleton-number" /> : docCount}
          </div>

          <div className="metric-label">Documents</div>
          <p className="metric-description">
            Project files currently available for retrieval.
          </p>
        </article>

        <article className="metric-card">
          <div className="metric-card-header">
            <span className="metric-icon">
              <Layers3 size={20} />
            </span>
            <span className="metric-status">Searchable</span>
          </div>

          <div className="metric-value">
            {loading ? <span className="skeleton-number" /> : chunkCount}
          </div>

          <div className="metric-label">Document chunks</div>
          <p className="metric-description">
            Embedded content segments stored for semantic search.
          </p>
        </article>

        <article className="metric-card">
          <div className="metric-card-header">
            <span className="metric-icon">
              <Database size={20} />
            </span>
            <span className="metric-status success">Ready</span>
          </div>

          <div className="metric-value metric-word">RAG</div>
          <div className="metric-label">Retrieval pipeline</div>
          <p className="metric-description">
            Feature-based retrieval and source references are enabled.
          </p>
        </article>

        <article className="metric-card">
          <div className="metric-card-header">
            <span className="metric-icon">
              <CheckCircle2 size={20} />
            </span>
            <span className="metric-status success">Active</span>
          </div>

          <div className="metric-value metric-word">Online</div>
          <div className="metric-label">System status</div>
          <p className="metric-description">
            The application is ready to generate and evaluate test cases.
          </p>
        </article>
      </section>

      <section className="dashboard-grid">
        <article className="card product-intro-card">
          <div className="card-heading-row">
            <div>
              <p className="eyebrow">About the workspace</p>
              <h2>Documentation-driven test generation</h2>
            </div>

            <span className="large-card-icon">
              <FlaskConical size={25} />
            </span>
          </div>

          <p className="card-description">
            TestPilot Lite RAG generates structured test cases from indexed
            project documentation. The system retrieves requirements related to
            the selected feature, creates requirement-grounded scenarios and
            evaluates coverage using the source documents.
          </p>

          <div className="feature-list">
            <div className="feature-item">
              <CheckCircle2 size={18} />
              <span>
                Generate positive, negative, validation, edge-case and security
                scenarios.
              </span>
            </div>

            <div className="feature-item">
              <CheckCircle2 size={18} />
              <span>
                Review source references and quality evaluation metrics.
              </span>
            </div>

            <div className="feature-item">
              <CheckCircle2 size={18} />
              <span>Export results as JSON, Markdown, CSV or Gherkin.</span>
            </div>
          </div>
        </article>

        <article className="card technology-card">
          <p className="eyebrow">Technology</p>
          <h2>Application stack</h2>

          <div className="stack-list">
            <div className="stack-item">
              <span>API</span>
              <strong>FastAPI</strong>
            </div>

            <div className="stack-item">
              <span>Vector database</span>
              <strong>ChromaDB</strong>
            </div>

            <div className="stack-item">
              <span>Embeddings</span>
              <strong>Sentence Transformers</strong>
            </div>

            <div className="stack-item">
              <span>Interface</span>
              <strong>React + TypeScript</strong>
            </div>
          </div>
        </article>
      </section>

      <section className="card workflow-section">
        <div className="section-heading">
          <div>
            <p className="eyebrow">Getting started</p>
            <h2>How the workflow operates</h2>
            <p>
              Complete these stages to move from project documentation to
              exportable test cases.
            </p>
          </div>
        </div>

        <div className="workflow-grid">
          <article className="workflow-step">
            <span className="step-number">01</span>
            <span className="workflow-icon">
              <UploadCloud size={22} />
            </span>
            <h3>Upload documentation</h3>
            <p>
              Add requirements, user stories, acceptance criteria or API
              specifications from the Documents page.
            </p>
          </article>

          <ArrowRight className="workflow-arrow" size={20} />

          <article className="workflow-step">
            <span className="step-number">02</span>
            <span className="workflow-icon">
              <Layers3 size={22} />
            </span>
            <h3>Index the content</h3>
            <p>
              Documents are divided into chunks, transformed into embeddings and
              stored for semantic retrieval.
            </p>
          </article>

          <ArrowRight className="workflow-arrow" size={20} />

          <article className="workflow-step">
            <span className="step-number">03</span>
            <span className="workflow-icon">
              <FlaskConical size={22} />
            </span>
            <h3>Generate test cases</h3>
            <p>
              Describe the feature, choose test types and create grounded
              scenarios using the indexed requirements.
            </p>
          </article>

          <ArrowRight className="workflow-arrow" size={20} />

          <article className="workflow-step">
            <span className="step-number">04</span>
            <span className="workflow-icon">
              <FileText size={22} />
            </span>
            <h3>Review and export</h3>
            <p>
              Inspect coverage, source references and test details before
              exporting the final result.
            </p>
          </article>
        </div>
      </section>
    </div>
  );
}

export default Dashboard;
