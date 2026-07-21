import ConfirmModal from "../components/ConfirmModal";
import { useEffect, useState, FormEvent } from "react";
import {
  generateTestCases,
  getProviders,
  GenerationResponse,
} from "../api/apiClient";

const testTypeOptions = [
  "Positive",
  "Negative",
  "Edge Case",
  "Validation",
  "Security",
];
const outputFormats = ["json", "markdown", "csv", "gherkin"];

type GenerationHistoryItem = {
  id: string;
  feature: string;
  query: string;
  outputFormat: string;
  provider: string;
  count: number;
  createdAt: string;
  preview: string;
};

function GenerateTests() {
  const [featureName, setFeatureName] = useState("");
  const [query, setQuery] = useState("");
  const [selectedTypes, setSelectedTypes] = useState<string[]>([
    "Positive",
    "Negative",
    "Edge Case",
  ]);
  const [numCases, setNumCases] = useState(5);
  const [outputFormat, setOutputFormat] = useState("json");
  const [provider, setProvider] = useState("mock");
  const [providerOptions, setProviderOptions] = useState<string[]>(["mock"]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [results, setResults] = useState<GenerationResponse | null>(null);
  const [history, setHistory] = useState<GenerationHistoryItem[]>([]);
  const [historySearch, setHistorySearch] = useState("");
  const [historyItemToDelete, setHistoryItemToDelete] =
    useState<GenerationHistoryItem | null>(null);

  useEffect(() => {
    const stored = window.localStorage.getItem("testpilot-history");
    if (stored) {
      try {
        setHistory(JSON.parse(stored));
      } catch {
        window.localStorage.removeItem("testpilot-history");
      }
    }

    getProviders()
      .then(setProviderOptions)
      .catch(() => setProviderOptions(["mock"]));
  }, []);

  const toggleTestType = (type: string) => {
    setSelectedTypes((prev) =>
      prev.includes(type) ? prev.filter((t) => t !== type) : [...prev, type],
    );
  };

  const saveHistory = (
    response: GenerationResponse,
    request: {
      featureName: string;
      query: string;
      outputFormat: string;
      provider: string;
    },
  ) => {
    const entry: GenerationHistoryItem = {
      id: `${Date.now()}`,
      feature: request.featureName,
      query: request.query,
      outputFormat: request.outputFormat,
      provider: request.provider,
      count: response.count,
      createdAt: new Date().toISOString(),
      preview: response.formatted.slice(0, 120),
    };

    const nextHistory = [entry, ...history].slice(0, 5);
    setHistory(nextHistory);
    window.localStorage.setItem(
      "testpilot-history",
      JSON.stringify(nextHistory),
    );
  };

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError("");
    setResults(null);

    try {
      if (!featureName.trim()) {
        throw new Error("Feature name is required");
      }
      if (!query.trim()) {
        throw new Error("Query is required");
      }
      if (selectedTypes.length === 0) {
        throw new Error("Select at least one test type");
      }

      const response = await generateTestCases(
        featureName,
        query,
        selectedTypes,
        numCases,
        outputFormat,
        provider,
      );
      setResults(response);
      saveHistory(response, { featureName, query, outputFormat, provider });
    } catch (err) {
      const message = err instanceof Error ? err.message : "Generation failed";
      setError(message);
    } finally {
      setLoading(false);
    }
  };

  const downloadFile = (content: string, filename: string, type: string) => {
    const blob = new Blob([content], { type });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  const handleExport = (format: string) => {
    if (!results) return;
    const timestamp = new Date().toISOString().slice(0, 10);
    const filename = `test_cases_${results.feature}_${timestamp}.${format}`;
    downloadFile(results.formatted, filename, "text/plain");
  };

  const handleDeleteHistoryItem = (id: string) => {
    const nextHistory = history.filter((item) => item.id !== id);

    setHistory(nextHistory);
    window.localStorage.setItem(
      "testpilot-history",
      JSON.stringify(nextHistory),
    );

    setHistoryItemToDelete(null);
  };

  const filteredHistory = history.filter((item) => {
    const searchTerm = historySearch.trim().toLowerCase();

    if (!searchTerm) {
      return true;
    }

    return (
      item.feature.toLowerCase().includes(searchTerm) ||
      item.query.toLowerCase().includes(searchTerm) ||
      item.provider.toLowerCase().includes(searchTerm) ||
      item.outputFormat.toLowerCase().includes(searchTerm)
    );
  });

  return (
    <div>
      <h1 className="section-title">Generate Test Cases</h1>

      <div className="card">
        <form onSubmit={handleSubmit}>
          <div className="form-row">
            <label>
              Feature/Module Name
              <input
                type="text"
                value={featureName}
                onChange={(e) => setFeatureName(e.target.value)}
                placeholder="e.g., Login, Password Reset, Payment"
                disabled={loading}
              />
            </label>
          </div>

          <div className="form-row">
            <label>
              Query/Description
              <textarea
                rows={5}
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Describe what test cases you need. This will search indexed documents for relevant content."
                disabled={loading}
              />
            </label>
          </div>

          <div className="form-row">
            <label>
              Test Types
              <div className="checkbox-group">
                {testTypeOptions.map((type) => (
                  <label key={type} className="checkbox-label">
                    <input
                      type="checkbox"
                      checked={selectedTypes.includes(type)}
                      onChange={() => toggleTestType(type)}
                      disabled={loading}
                    />
                    {type}
                  </label>
                ))}
              </div>
            </label>
          </div>

          <div className="form-row">
            <label>
              Number of Test Cases
              <input
                type="number"
                value={numCases}
                onChange={(e) =>
                  setNumCases(Math.max(1, parseInt(e.target.value) || 1))
                }
                min="1"
                max="20"
                disabled={loading}
              />
            </label>
            <label>
              Output Format
              <select
                value={outputFormat}
                onChange={(e) => setOutputFormat(e.target.value)}
                disabled={loading}
              >
                {outputFormats.map((fmt) => (
                  <option key={fmt} value={fmt}>
                    {fmt.toUpperCase()}
                  </option>
                ))}
              </select>
            </label>
            <label>
              LLM Provider
              <select
                value={provider}
                onChange={(e) => setProvider(e.target.value)}
                disabled={loading}
              >
                {providerOptions.map((option) => (
                  <option key={option} value={option}>
                    {option
                      .replace("_", " ")
                      .replace(/\b\w/g, (c) => c.toUpperCase())}
                  </option>
                ))}
              </select>
            </label>
          </div>

          <div className="form-row">
            <button type="submit" disabled={loading} className="btn-primary">
              {loading ? "Generating..." : "Generate Test Cases"}
            </button>
          </div>
        </form>

        {error && <div className="error-message">{error}</div>}
      </div>

      {history.length > 0 && (
        <div className="card">
          <div className="history-header">
            <div>
              <h2 className="section-title">Recent Generations</h2>
              <p className="history-count">
                {filteredHistory.length} of {history.length} generations
              </p>
            </div>

            <div className="history-search-wrapper">
              <input
                type="search"
                value={historySearch}
                onChange={(e) => setHistorySearch(e.target.value)}
                placeholder="Search history..."
                className="history-search"
                aria-label="Search generation history"
              />

              {historySearch && (
                <button
                  type="button"
                  className="history-search-clear"
                  onClick={() => setHistorySearch("")}
                  aria-label="Clear history search"
                >
                  ×
                </button>
              )}
            </div>
          </div>

          {filteredHistory.length > 0 ? (
            <div className="history-list">
              {filteredHistory.map((item) => (
                <div key={item.id} className="history-item">
                  <div className="history-item-header">
                    <div className="history-meta">
                      <strong>{item.feature}</strong>
                      <span className="pill">
                        {item.outputFormat.toUpperCase()}
                      </span>
                      <span className="pill">
                        {item.provider.toUpperCase()}
                      </span>
                    </div>

                    <button
                      type="button"
                      className="history-delete-button"
                      onClick={() => setHistoryItemToDelete(item)}
                      aria-label={`Delete ${item.feature} from history`}
                      title="Delete generation"
                    >
                      Delete
                    </button>
                  </div>

                  <p>{item.query}</p>

                  <small>
                    {item.count} cases ·{" "}
                    {new Date(item.createdAt).toLocaleString()}
                  </small>
                </div>
              ))}
            </div>
          ) : (
            <div className="empty-state">
              No generation history matches “{historySearch}”.
            </div>
          )}
        </div>
      )}

      {results && (
        <div className="card">
          <h2 className="section-title">
            Generated Test Cases ({results.count})
          </h2>
          <p>
            <strong>Feature:</strong> {results.feature} |{" "}
            <strong>Retrieved chunks:</strong> {results.retrieved_chunks}
          </p>
          <p>
            <strong>Provider:</strong> {results.provider.toUpperCase()}
          </p>

          <div className="export-buttons">
            {outputFormats.map((fmt) => (
              <button
                key={fmt}
                onClick={() => handleExport(fmt)}
                className="btn-secondary"
              >
                Export as {fmt.toUpperCase()}
              </button>
            ))}
          </div>

          {results.test_cases.length === 0 ? (
            <div className="empty-state">
              No test cases were generated. Try broadening the query or adding
              more documents.
            </div>
          ) : (
            <div className="test-cases-container">
              {results.test_cases.map((tc) => (
                <div key={tc.id} className="test-case-card">
                  <div className="tc-header">
                    <h3>{tc.title}</h3>
                    <span className={`badge badge-${tc.type.toLowerCase()}`}>
                      {tc.type}
                    </span>
                    <span
                      className={`badge badge-priority-${tc.priority.toLowerCase()}`}
                    >
                      {tc.priority}
                    </span>
                  </div>

                  <div className="tc-section">
                    <strong>Preconditions:</strong>
                    <ul>
                      {tc.preconditions.map((pre, i) => (
                        <li key={i}>{pre}</li>
                      ))}
                    </ul>
                  </div>

                  <div className="tc-section">
                    <strong>Test Steps:</strong>
                    <ol>
                      {tc.steps.map((step, i) => (
                        <li key={i}>{step}</li>
                      ))}
                    </ol>
                  </div>

                  <div className="tc-section">
                    <strong>Expected Result:</strong>
                    <p>{tc.expected_result}</p>
                  </div>

                  {tc.source_references.length > 0 && (
                    <div className="tc-section">
                      <strong>Source References:</strong>
                      <ul>
                        {tc.source_references.map((ref, idx) => (
                          <li key={idx}>
                            <strong>{ref.document_name}</strong>
                            {ref.chunk_id ? ` (${ref.chunk_id})` : ""}
                            {ref.quote ? ` — ${ref.quote}` : ""}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}

          <div className="formatted-output">
            <h3>Formatted Output ({outputFormat.toUpperCase()})</h3>
            <pre>{results.formatted}</pre>
          </div>

          {results.evaluation && (
            <div className="quality-summary">
              <h3>Quality Evaluation</h3>
              <div className="metrics-row">
                <div className="metric-small">
                  <div className="metric-label">Coverage</div>
                  <div className="metric-value-small">
                    {results.evaluation.coverage_score}%
                  </div>
                </div>
                <div className="metric-small">
                  <div className="metric-label">Completeness</div>
                  <div className="metric-value-small">
                    {results.evaluation.completeness_score}%
                  </div>
                </div>
                <div className="metric-small">
                  <div className="metric-label">Groundedness</div>
                  <div className="metric-value-small">
                    {results.evaluation.groundedness_score}%
                  </div>
                </div>
              </div>
              <p>
                <strong>Recommendation:</strong>{" "}
                {results.evaluation.recommendation}
              </p>
              {results.evaluation.issues.length > 0 && (
                <div>
                  <strong>
                    Issues Found ({results.evaluation.issues_found}):
                  </strong>
                  <ul>
                    {results.evaluation.issues.map((issue, i) => (
                      <li key={i}>{issue}</li>
                    ))}
                  </ul>
                </div>
              )}
              <div>
                <strong>Test Type Distribution:</strong>
                <ul>
                  {Object.entries(results.evaluation.type_distribution).map(
                    ([type, count]) => (
                      <li key={type}>
                        {type}: {count}
                      </li>
                    ),
                  )}
                </ul>
              </div>
            </div>
          )}
        </div>
      )}

      <ConfirmModal
        isOpen={historyItemToDelete !== null}
        title="Delete Generation"
        message="Are you sure you want to remove this generation from your history?"
        warning="This action cannot be undone."
        confirmText="Delete"
        cancelText="Cancel"
        onCancel={() => setHistoryItemToDelete(null)}
        onConfirm={() => {
          if (historyItemToDelete) {
            handleDeleteHistoryItem(historyItemToDelete.id);
          }
        }}
      />
    </div>
  );
}

export default GenerateTests;
