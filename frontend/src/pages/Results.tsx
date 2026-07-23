import { useEffect, useMemo, useState } from "react";
import {
  BarChart3,
  CheckCircle2,
  ClipboardCheck,
  Download,
  FileJson,
  FileText,
  Info,
  Layers3,
  ShieldCheck,
} from "lucide-react";

import type { GenerationResponse } from "../api/apiClient";

import {
  readGenerationHistory,
  sortGenerationHistory,
} from "../types/generationHistory";

import type { GenerationHistoryItem } from "../types/generationHistory";

type ResultsProps = {
  selectedHistoryId: string | null;
  onSelectedHistoryIdChange: (historyId: string | null) => void;
};

function InfoTooltip({ text }: { text: string }) {
  return (
    <span className="info-tooltip">
      <button
        type="button"
        className="info-tooltip-trigger"
        aria-label="Show information"
      >
        <Info size={15} />
      </button>

      <span className="info-tooltip-content" role="tooltip">
        {text}
      </span>
    </span>
  );
}

function Results({
  selectedHistoryId,
  onSelectedHistoryIdChange,
}: ResultsProps) {
  const [history, setHistory] = useState<GenerationHistoryItem[]>([]);

  const [showPageHelp, setShowPageHelp] = useState(false);

  useEffect(() => {
    const storedHistory = sortGenerationHistory(readGenerationHistory()).filter(
      (item) => Boolean(item.response),
    );

    setHistory(storedHistory);
  }, []);

  useEffect(() => {
    if (history.length === 0) {
      if (selectedHistoryId !== null) {
        onSelectedHistoryIdChange(null);
      }

      return;
    }

    const selectedExists = history.some(
      (item) => item.id === selectedHistoryId,
    );

    if (!selectedExists) {
      onSelectedHistoryIdChange(history[0].id);
    }
  }, [history, selectedHistoryId, onSelectedHistoryIdChange]);

  const selectedItem = useMemo(
    () =>
      history.find((item) => item.id === selectedHistoryId) ??
      history[0] ??
      null,
    [history, selectedHistoryId],
  );

  const result: GenerationResponse | null = selectedItem?.response ?? null;

  const downloadFile = (
    content: string,
    filename: string,
    mimeType: string,
  ) => {
    const blob = new Blob([content], {
      type: mimeType,
    });

    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");

    anchor.href = url;
    anchor.download = filename;

    document.body.appendChild(anchor);
    anchor.click();
    document.body.removeChild(anchor);

    URL.revokeObjectURL(url);
  };

  const normalizedFeature =
    result?.feature
      .trim()
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, "_") || "test_cases";

  const exportOriginal = () => {
    if (!result || !selectedItem) {
      return;
    }

    const extension = selectedItem.outputFormat.toLowerCase();

    downloadFile(
      result.formatted,
      `${normalizedFeature}.${extension}`,
      "text/plain;charset=utf-8",
    );
  };

  const exportJson = () => {
    if (!result) {
      return;
    }

    downloadFile(
      JSON.stringify(result.test_cases, null, 2),
      `${normalizedFeature}.json`,
      "application/json;charset=utf-8",
    );
  };

  return (
    <div className="page-stack results-page">
      <header className="page-header">
        <div>
          <p className="eyebrow">Generated Output</p>

          <div className="title-with-info">
            <h1>Results</h1>

            <InfoTooltip text="Select and review any generation saved in your local history." />
          </div>

          <p className="page-description">
            Select a previous generation and review its test cases, source
            references and quality evaluation.
          </p>

          <div className="page-help-wrapper">
            <button
              type="button"
              className="page-help-button"
              aria-expanded={showPageHelp}
              onClick={() => setShowPageHelp((current) => !current)}
            >
              <Info size={16} />
              How to read these results
            </button>

            {showPageHelp && (
              <div className="page-help-panel">
                <p>
                  Coverage shows how many extracted requirements are addressed.
                  Completeness checks the structure of generated cases.
                  Groundedness shows whether the scenarios are supported by
                  retrieved documents.
                </p>
              </div>
            )}
          </div>
        </div>
      </header>

      {history.length === 0 || !result ? (
        <section className="card results-empty-card">
          <span className="results-empty-icon">
            <ClipboardCheck size={34} />
          </span>

          <h2>No saved results yet</h2>

          <p>
            Generate test cases from the Generate Tests page. The result will be
            saved and displayed here.
          </p>
        </section>
      ) : (
        <>
          <section className="card result-selector-card">
            <label className="field-group">
              <span className="field-label">
                Viewing generation
                <InfoTooltip text="Select any saved generation result from your local history." />
              </span>

              <select
                value={selectedItem?.id ?? ""}
                onChange={(event) =>
                  onSelectedHistoryIdChange(event.target.value)
                }
              >
                {history.map((item) => (
                  <option key={item.id} value={item.id}>
                    {item.feature} · {item.count} cases ·{" "}
                    {new Date(item.createdAt).toLocaleString()}
                    {item.isPinned ? " · Favorite" : ""}
                  </option>
                ))}
              </select>
            </label>
          </section>

          <section className="card results-overview-card">
            <div className="results-overview-header">
              <div>
                <p className="eyebrow">Selected generation</p>

                <h2>{result.feature}</h2>

                <p>{selectedItem?.query}</p>
              </div>

              <div className="results-provider">
                <span>Provider</span>
                <strong>{result.provider.toUpperCase()}</strong>
              </div>
            </div>

            <div className="results-meta-row">
              <span>
                <Layers3 size={16} />
                {result.retrieved_chunks} retrieved chunks
              </span>

              <span>
                <ClipboardCheck size={16} />
                {result.count} test cases
              </span>

              <span>
                <FileText size={16} />
                {new Date(selectedItem?.createdAt ?? "").toLocaleString()}
              </span>
            </div>
          </section>

          {result.evaluation && (
            <section className="results-metrics-grid">
              <article className="result-metric-card">
                <div className="result-metric-header">
                  <span className="result-metric-icon">
                    <BarChart3 size={20} />
                  </span>

                  <InfoTooltip text="Percentage of extracted requirements addressed by the generated tests." />
                </div>

                <strong>{result.evaluation.coverage_score}%</strong>

                <span>Coverage</span>
                <p>Requirements addressed by the scenarios.</p>
              </article>

              <article className="result-metric-card">
                <div className="result-metric-header">
                  <span className="result-metric-icon">
                    <CheckCircle2 size={20} />
                  </span>

                  <InfoTooltip text="Percentage of test cases containing all required fields." />
                </div>

                <strong>{result.evaluation.completeness_score}%</strong>

                <span>Completeness</span>
                <p>Test cases with complete structured details.</p>
              </article>

              <article className="result-metric-card">
                <div className="result-metric-header">
                  <span className="result-metric-icon">
                    <ShieldCheck size={20} />
                  </span>

                  <InfoTooltip text="Percentage of generated cases supported by retrieved source documents." />
                </div>

                <strong>{result.evaluation.groundedness_score}%</strong>

                <span>Groundedness</span>
                <p>Scenarios supported by indexed sources.</p>
              </article>
            </section>
          )}

          <section className="card results-export-card">
            <div className="results-section-header">
              <div>
                <p className="eyebrow">Export</p>
                <h2>Download selected result</h2>

                <p>
                  Download the original formatted output or a JSON
                  representation of the generated test cases.
                </p>
              </div>

              <Download size={22} />
            </div>

            <div className="results-export-buttons">
              <button
                type="button"
                className="result-export-button"
                onClick={exportOriginal}
              >
                <FileText size={17} />
                Original {selectedItem?.outputFormat.toUpperCase()}
              </button>

              <button
                type="button"
                className="result-export-button"
                onClick={exportJson}
              >
                <FileJson size={17} />
                JSON
              </button>
            </div>
          </section>

          <section className="results-test-list">
            <div className="results-section-header">
              <div>
                <p className="eyebrow">Test Scenarios</p>
                <h2>Generated Test Cases ({result.count})</h2>
              </div>
            </div>

            {(result.test_cases ?? []).map((testCase, testIndex) => (
              <article key={testCase.id} className="result-test-card">
                <div className="result-test-card-header">
                  <span className="result-test-index">
                    {String(testIndex + 1).padStart(2, "0")}
                  </span>

                  <div className="result-test-title">
                    <h3>{testCase.title}</h3>

                    <div className="result-test-badges">
                      <span
                        className={`badge badge-${testCase.type
                          .toLowerCase()
                          .replace(/\s+/g, "-")}`}
                      >
                        {testCase.type}
                      </span>

                      <span
                        className={`badge badge-priority-${testCase.priority.toLowerCase()}`}
                      >
                        {testCase.priority}
                      </span>
                    </div>
                  </div>
                </div>

                <div className="result-test-content-grid">
                  <section className="result-detail-section">
                    <h4>Preconditions</h4>

                    <ul>
                      {testCase.preconditions.map((precondition, index) => (
                        <li key={index}>{precondition}</li>
                      ))}
                    </ul>
                  </section>

                  <section className="result-detail-section">
                    <h4>Expected Result</h4>
                    <p>{testCase.expected_result}</p>
                  </section>
                </div>

                <section className="result-detail-section">
                  <h4>Test Steps</h4>

                  <ol className="result-steps-list">
                    {testCase.steps.map((step, index) => (
                      <li key={index}>
                        <span>{index + 1}</span>
                        <p>{step}</p>
                      </li>
                    ))}
                  </ol>
                </section>

                {(testCase.source_references?.length ?? 0) > 0 && (
                  <section className="result-source-section">
                    <div className="result-source-title">
                      <FileText size={17} />
                      <h4>Source References</h4>
                    </div>

                    <div className="result-source-list">
                      {testCase.source_references?.map((reference, index) => (
                        <article key={index} className="result-source-item">
                          <strong>{reference.document_name}</strong>

                          {reference.chunk_id && (
                            <span>{reference.chunk_id}</span>
                          )}

                          {reference.quote && <p>{reference.quote}</p>}
                        </article>
                      ))}
                    </div>
                  </section>
                )}
              </article>
            ))}
          </section>
        </>
      )}
    </div>
  );
}

export default Results;
