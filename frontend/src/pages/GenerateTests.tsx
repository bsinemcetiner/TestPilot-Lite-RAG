import DuplicateWarningModal from "../components/DuplicateWarningModal";
import { useEffect, useState } from "react";
import type { FormEvent } from "react";
import {
  Braces,
  CheckCircle2,
  FileOutput,
  Info,
  Layers3,
  LoaderCircle,
  Search,
  Settings2,
  ShieldCheck,
} from "lucide-react";
import { generateTestCases, getProviders } from "../api/apiClient";

import type { GenerationResponse } from "../api/apiClient";

import {
  readGenerationHistory,
  writeGenerationHistory,
} from "../types/generationHistory";

import type { GenerationHistoryItem } from "../types/generationHistory";

const testTypeOptions = [
  "Positive",
  "Negative",
  "Edge Case",
  "Validation",
  "Security",
];
const outputFormats = ["json", "markdown", "csv", "gherkin"];

const normalizeText = (value: string) =>
  value.trim().toLowerCase().replace(/\s+/g, " ");

type GenerationRequest = {
  featureName: string;
  query: string;
  outputFormat: string;
  provider: string;
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

type GenerateTestsProps = {
  onOpenResults: (historyId?: string) => void;
};

function GenerateTests({ onOpenResults }: GenerateTestsProps) {
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

  const [history, setHistory] = useState<GenerationHistoryItem[]>([]);

  const [duplicateItem, setDuplicateItem] =
    useState<GenerationHistoryItem | null>(null);
  const [showPageHelp, setShowPageHelp] = useState(false);

  const [pendingGeneration, setPendingGeneration] =
    useState<GenerationRequest | null>(null);

  useEffect(() => {
    setHistory(readGenerationHistory());

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
    request: GenerationRequest,
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
      isPinned: false,
      response,
    };

    const currentHistory = readGenerationHistory();

    const nextHistory = [entry, ...currentHistory].slice(0, 20);

    setHistory(nextHistory);
    writeGenerationHistory(nextHistory);

    return entry;
  };

  const executeGeneration = async (request: GenerationRequest) => {
    setLoading(true);
    setError("");

    try {
      const response = await generateTestCases(
        request.featureName,
        request.query,
        selectedTypes,
        numCases,
        request.outputFormat,
        request.provider,
      );

      const savedEntry = saveHistory(response, request);

      onOpenResults(savedEntry.id);
    } catch (err) {
      const message = err instanceof Error ? err.message : "Generation failed";

      setError(message);
    } finally {
      setLoading(false);
      setPendingGeneration(null);
      setDuplicateItem(null);
    }
  };

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError("");

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

      const request: GenerationRequest = {
        featureName: featureName.trim(),
        query: query.trim(),
        outputFormat,
        provider,
      };

      const duplicate = history.find(
        (item) =>
          normalizeText(item.feature) === normalizeText(request.featureName) &&
          normalizeText(item.query) === normalizeText(request.query),
      );

      if (duplicate) {
        setPendingGeneration(request);
        setDuplicateItem(duplicate);
        return;
      }

      await executeGeneration(request);
    } catch (err) {
      const message = err instanceof Error ? err.message : "Generation failed";

      setError(message);
    }
  };

  return (
    <div className="page-stack generate-page">
      <header className="page-header">
        <div>
          <p className="eyebrow">Test Generation</p>

          <div className="title-with-info">
            <h1>Generate Test Cases</h1>

            <InfoTooltip text="Generate structured test cases using requirements retrieved from your indexed project documents." />
          </div>

          <p className="page-description">
            Select a feature, describe the scenarios you need and generate
            requirement-based test cases using the indexed knowledge base.
          </p>

          <div className="page-help-wrapper">
            <button
              type="button"
              className="page-help-button"
              onClick={() => setShowPageHelp((current) => !current)}
              aria-expanded={showPageHelp}
            >
              <Info size={16} />
              How generation works
            </button>

            {showPageHelp && (
              <div className="page-help-panel">
                <p>
                  The system searches indexed documents for requirements related
                  to the feature name and description. It then creates the
                  selected test types, formats the output and evaluates
                  coverage, completeness and groundedness.
                </p>
              </div>
            )}
          </div>
        </div>
      </header>

      <section className="card generation-form-card">
        <div className="card-heading-row">
          <div>
            <p className="eyebrow">Generation request</p>
            <h2>Configure the test scenarios</h2>
            <p className="card-description">
              Provide enough feature context for accurate document retrieval and
              scenario generation.
            </p>
          </div>
        </div>

        <form onSubmit={handleSubmit} className="modern-generation-form">
          <section className="generation-form-section">
            <div className="generation-section-heading">
              <span className="generation-section-icon">
                <Search size={19} />
              </span>

              <div>
                <h3>Feature information</h3>
                <p>
                  Tell the system which product feature should be matched with
                  indexed requirements.
                </p>
              </div>
            </div>

            <div className="generation-fields-grid">
              <label className="field-group">
                <span className="field-label">
                  Feature or module name
                  <InfoTooltip text="This value is used to retrieve chunks belonging to the requested feature. It should match the feature name in your indexed document." />
                </span>

                <input
                  type="text"
                  value={featureName}
                  onChange={(event) => setFeatureName(event.target.value)}
                  placeholder="e.g. User Registration"
                  disabled={loading}
                />

                <span className="field-hint">
                  Use the same feature name found in the source document.
                </span>
              </label>

              <label className="field-group">
                <span className="field-label">
                  Number of test cases
                  <InfoTooltip text="Choose how many test cases should be generated. The supported range is 1 to 20." />
                </span>

                <div className="number-input-wrapper">
                  <input
                    type="number"
                    value={numCases}
                    onChange={(event) =>
                      setNumCases(
                        Math.min(
                          20,
                          Math.max(1, parseInt(event.target.value) || 1),
                        ),
                      )
                    }
                    min="1"
                    max="20"
                    disabled={loading}
                  />

                  <span>1–20 cases</span>
                </div>
              </label>
            </div>

            <label className="field-group">
              <span className="field-label">
                Query or description
                <InfoTooltip text="Describe the scenarios you need. The query is combined with the feature name when searching the indexed documents." />
              </span>

              <textarea
                rows={5}
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                placeholder="Describe the required scenarios, test focus and expected coverage..."
                disabled={loading}
              />

              <span className="field-hint">
                Example: Generate comprehensive test cases based only on the
                retrieved registration requirements.
              </span>
            </label>
          </section>

          <section className="generation-form-section">
            <div className="generation-section-heading">
              <span className="generation-section-icon">
                <Layers3 size={19} />
              </span>

              <div>
                <h3>Test coverage</h3>
                <p>
                  Choose the scenario categories that should appear in the
                  generated output.
                </p>
              </div>
            </div>

            <div className="test-type-grid">
              {testTypeOptions.map((type) => {
                const selected = selectedTypes.includes(type);

                return (
                  <button
                    key={type}
                    type="button"
                    className={`test-type-card ${selected ? "selected" : ""}`}
                    onClick={() => toggleTestType(type)}
                    disabled={loading}
                    aria-pressed={selected}
                  >
                    <span className="test-type-check">
                      {selected ? (
                        <CheckCircle2 size={18} />
                      ) : (
                        <span className="test-type-empty-check" />
                      )}
                    </span>

                    <span>
                      <strong>{type}</strong>
                      <small>
                        {type === "Positive" &&
                          "Expected behavior with valid input"}
                        {type === "Negative" &&
                          "Invalid input and rejected actions"}
                        {type === "Edge Case" &&
                          "Boundary and unusual conditions"}
                        {type === "Validation" &&
                          "Input rules and required fields"}
                        {type === "Security" &&
                          "Malicious input and protection checks"}
                      </small>
                    </span>
                  </button>
                );
              })}
            </div>
          </section>

          <section className="generation-form-section">
            <div className="generation-section-heading">
              <span className="generation-section-icon">
                <Settings2 size={19} />
              </span>

              <div>
                <h3>Generation settings</h3>
                <p>
                  Configure the provider and the format used for the generated
                  response.
                </p>
              </div>
            </div>

            <div className="generation-settings-grid">
              <label className="field-group">
                <span className="field-label">
                  Output format
                  <InfoTooltip text="Controls the formatted output displayed and saved with the generation result." />
                </span>

                <div className="select-with-icon">
                  <FileOutput size={17} />

                  <select
                    value={outputFormat}
                    onChange={(event) => setOutputFormat(event.target.value)}
                    disabled={loading}
                  >
                    {outputFormats.map((formatOption) => (
                      <option key={formatOption} value={formatOption}>
                        {formatOption.toUpperCase()}
                      </option>
                    ))}
                  </select>
                </div>
              </label>

              <label className="field-group">
                <span className="field-label">
                  LLM provider
                  <InfoTooltip text="Selects the configured provider used to create test cases. The local mock provider works without an external API." />
                </span>

                <div className="select-with-icon">
                  <Braces size={17} />

                  <select
                    value={provider}
                    onChange={(event) => setProvider(event.target.value)}
                    disabled={loading}
                  >
                    {providerOptions.map((option) => (
                      <option key={option} value={option}>
                        {option
                          .replace("_", " ")
                          .replace(/\b\w/g, (character) =>
                            character.toUpperCase(),
                          )}
                      </option>
                    ))}
                  </select>
                </div>
              </label>
            </div>
          </section>

          {error && (
            <div className="generation-error-message" role="alert">
              <ShieldCheck size={18} />
              <span>{error}</span>
            </div>
          )}

          <button
            type="submit"
            disabled={loading}
            className="btn-primary generate-tests-button"
          >
            {loading ? (
              <>
                <LoaderCircle className="button-spinner" size={19} />
                Retrieving requirements and generating tests...
              </>
            ) : (
              <>Generate Test Cases</>
            )}
          </button>
        </form>
      </section>

      <DuplicateWarningModal
        isOpen={duplicateItem !== null}
        feature={duplicateItem?.feature ?? ""}
        createdAt={duplicateItem?.createdAt ?? ""}
        canViewPrevious={Boolean(duplicateItem?.response)}
        onCancel={() => {
          setDuplicateItem(null);
          setPendingGeneration(null);
        }}
        onViewPrevious={() => {
          if (!duplicateItem?.response) return;

          const historyId = duplicateItem.id;

          setDuplicateItem(null);
          setPendingGeneration(null);

          onOpenResults(historyId);
        }}
        onGenerateAnyway={() => {
          if (!pendingGeneration) return;

          const request = pendingGeneration;

          setDuplicateItem(null);
          setPendingGeneration(null);

          executeGeneration(request);
        }}
      />
    </div>
  );
}

export default GenerateTests;
