import { useState } from "react";
import {
  BarChart3,
  Clock3,
  FileText,
  FlaskConical,
  HelpCircle,
  LayoutDashboard,
} from "lucide-react";

import Dashboard from "./pages/Dashboard";
import Documents from "./pages/Documents";
import GenerateTests from "./pages/GenerateTests";
import Results from "./pages/Results";
import History from "./pages/History";
import "./App.css";

type PageKey =
  | "dashboard"
  | "documents"
  | "generate"
  | "results"
  | "history"
  | "help";

const pages = [
  {
    key: "dashboard" as PageKey,
    label: "Dashboard",
    description: "Project overview",
    icon: LayoutDashboard,
  },
  {
    key: "documents" as PageKey,
    label: "Documents",
    description: "Upload and index",
    icon: FileText,
  },
  {
    key: "generate" as PageKey,
    label: "Generate Tests",
    description: "Create test cases",
    icon: FlaskConical,
  },
  {
    key: "results" as PageKey,
    label: "Results",
    description: "Review generated tests",
    icon: BarChart3,
  },
  {
    key: "history" as PageKey,
    label: "History",
    description: "Previous generations",
    icon: Clock3,
  },
  {
    key: "help" as PageKey,
    label: "Help",
    description: "How to use TestPilot",
    icon: HelpCircle,
  },
];

function Help() {
  return (
    <div className="page-stack">
      <header className="page-header">
        <div>
          <p className="eyebrow">Documentation</p>
          <h1>Help Center</h1>

          <p className="page-description">
            Learn how each part of TestPilot Lite RAG fits into the test
            generation workflow.
          </p>
        </div>
      </header>

      <div className="help-grid">
        <article className="card help-card">
          <LayoutDashboard size={22} />

          <div>
            <h2>Dashboard</h2>
            <p>
              View indexed document counts, chunk totals and the current state
              of the retrieval pipeline.
            </p>
          </div>
        </article>

        <article className="card help-card">
          <FileText size={22} />

          <div>
            <h2>Documents</h2>
            <p>
              Add requirements, user stories, acceptance criteria or API
              specifications to the indexed knowledge base.
            </p>
          </div>
        </article>

        <article className="card help-card">
          <FlaskConical size={22} />

          <div>
            <h2>Generate Tests</h2>
            <p>
              Enter a feature name, describe the required scenarios, select test
              types and start generation.
            </p>
          </div>
        </article>

        <article className="card help-card">
          <BarChart3 size={22} />

          <div>
            <h2>Results</h2>
            <p>
              Select any saved generation and review its test cases, source
              references and quality metrics.
            </p>
          </div>
        </article>

        <article className="card help-card">
          <Clock3 size={22} />

          <div>
            <h2>History</h2>
            <p>
              Search saved generations, mark important results as favorites or
              remove old records.
            </p>
          </div>
        </article>
      </div>
    </div>
  );
}

function App() {
  const [currentPage, setCurrentPage] = useState<PageKey>("dashboard");

  const [selectedResultId, setSelectedResultId] = useState<string | null>(null);

  const openResults = (historyId?: string) => {
    setSelectedResultId(historyId ?? null);
    setCurrentPage("results");
  };

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand-area">
          <div className="brand-mark">
            <FlaskConical size={21} />
          </div>

          <div>
            <div className="brand">TestPilot</div>
            <div className="brand-subtitle">Lite RAG</div>

            <div className="brand-tagline">
              Generate Test Cases
              <br />
              from Requirements
            </div>
          </div>
        </div>

        <nav className="sidebar-nav">
          <span className="nav-section-label">Workspace</span>

          {pages.map((page) => {
            const Icon = page.icon;
            const isActive = currentPage === page.key;

            return (
              <button
                key={page.key}
                type="button"
                className={`nav-item ${isActive ? "active" : ""}`}
                onClick={() => setCurrentPage(page.key)}
              >
                <span className="nav-icon">
                  <Icon size={19} strokeWidth={1.9} />
                </span>

                <span className="nav-copy">
                  <span className="nav-label">{page.label}</span>

                  <span className="nav-description">{page.description}</span>
                </span>
              </button>
            );
          })}
        </nav>

        <div className="sidebar-footer">
          <div className="system-indicator">
            <span className="status-dot" />

            <div>
              <strong>System online</strong>
              <span>RAG pipeline available</span>
            </div>
          </div>

          <span className="version-label">TestPilot Lite RAG · v1.0</span>
        </div>
      </aside>

      <main className="content">
        {currentPage === "dashboard" && <Dashboard />}

        {currentPage === "documents" && <Documents />}

        {currentPage === "generate" && (
          <GenerateTests onOpenResults={openResults} />
        )}

        {currentPage === "results" && (
          <Results
            selectedHistoryId={selectedResultId}
            onSelectedHistoryIdChange={setSelectedResultId}
          />
        )}

        {currentPage === "history" && <History onOpenResults={openResults} />}

        {currentPage === "help" && <Help />}
      </main>
    </div>
  );
}

export default App;
