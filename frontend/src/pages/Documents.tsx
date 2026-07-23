import {
  ChangeEvent,
  DragEvent,
  FormEvent,
  useEffect,
  useRef,
  useState,
} from "react";
import {
  CheckCircle2,
  FileText,
  Info,
  Layers3,
  LoaderCircle,
  UploadCloud,
  X,
} from "lucide-react";

import {
  DocumentRecord,
  getChunkCount,
  getDocuments,
  uploadDocumentFile,
  uploadDocumentText,
} from "../api/apiClient";

const documentFormats = ["md", "txt", "json", "yaml"];

type DocumentWithChunks = DocumentRecord & {
  chunk_count?: number;
};

type UploadMethod = "text" | "file";

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

function Documents() {
  const [documents, setDocuments] = useState<DocumentWithChunks[]>([]);
  const [loading, setLoading] = useState(false);
  const [loadingDocuments, setLoadingDocuments] = useState(false);
  const [message, setMessage] = useState("");
  const [isError, setIsError] = useState(false);

  const [name, setName] = useState("");
  const [format, setFormat] = useState("md");
  const [sourceType, setSourceType] = useState("");
  const [content, setContent] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [uploadMethod, setUploadMethod] = useState<UploadMethod>("text");
  const [isDragging, setIsDragging] = useState(false);

  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const [showPageHelp, setShowPageHelp] = useState(false);

  useEffect(() => {
    void fetchDocuments();
  }, []);

  const fetchDocuments = async () => {
    setLoadingDocuments(true);

    try {
      const docs = await getDocuments();

      const documentsWithChunks = await Promise.all(
        docs.map(async (doc) => {
          try {
            const chunkCount = await getChunkCount(doc.id);

            return {
              ...doc,
              chunk_count: chunkCount,
            };
          } catch {
            console.error(`Failed to get chunk count for document ${doc.id}`);

            return {
              ...doc,
              chunk_count: undefined,
            };
          }
        }),
      );

      setDocuments(documentsWithChunks);
    } catch {
      setMessage("Could not load indexed documents.");
      setIsError(true);
    } finally {
      setLoadingDocuments(false);
    }
  };

  const resetForm = () => {
    setName("");
    setFormat("md");
    setSourceType("");
    setContent("");
    setFile(null);

    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  };

  const selectUploadMethod = (method: UploadMethod) => {
    setUploadMethod(method);
    setMessage("");
    setIsError(false);
  };

  const updateFormatFromFile = (selectedFile: File) => {
    const extension = selectedFile.name.split(".").pop()?.toLowerCase();

    if (extension === "yml") {
      setFormat("yaml");
      return;
    }

    if (extension && documentFormats.includes(extension)) {
      setFormat(extension);
    }
  };

  const setSelectedFile = (selectedFile: File | null) => {
    if (!selectedFile) {
      setFile(null);
      return;
    }

    const allowedExtensions = [".txt", ".md", ".json", ".yaml", ".yml"];

    const lowerName = selectedFile.name.toLowerCase();
    const isSupported = allowedExtensions.some((extension) =>
      lowerName.endsWith(extension),
    );

    if (!isSupported) {
      setMessage(
        "Unsupported file type. Please select TXT, MD, JSON, YAML or YML.",
      );
      setIsError(true);
      return;
    }

    setFile(selectedFile);
    updateFormatFromFile(selectedFile);
    setMessage("");
    setIsError(false);

    if (!name.trim()) {
      const nameWithoutExtension = selectedFile.name.replace(/\.[^/.]+$/, "");

      setName(nameWithoutExtension);
    }
  };

  const handleFileChange = (event: ChangeEvent<HTMLInputElement>) => {
    setSelectedFile(event.target.files?.[0] ?? null);
  };

  const handleDragOver = (event: DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = () => {
    setIsDragging(false);
  };

  const handleDrop = (event: DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    setIsDragging(false);

    setSelectedFile(event.dataTransfer.files?.[0] ?? null);
  };

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault();
    setMessage("");
    setIsError(false);

    if (uploadMethod === "file" && !file) {
      setMessage("Please select a document file.");
      setIsError(true);
      return;
    }

    if (uploadMethod === "text" && !content.trim()) {
      setMessage("Please enter document content.");
      setIsError(true);
      return;
    }

    setLoading(true);

    try {
      let created;

      if (uploadMethod === "file" && file) {
        created = await uploadDocumentFile(
          name.trim() || file.name,
          format,
          sourceType.trim(),
          file,
        );
      } else {
        created = await uploadDocumentText({
          name: name.trim() || "Untitled document",
          content: content.trim(),
          format,
          source_type: sourceType.trim() || undefined,
        });
      }

      setMessage(
        `Document "${created.name}" was uploaded and indexed successfully.`,
      );
      setIsError(false);

      resetForm();
      await fetchDocuments();
    } catch (error) {
      const errorMessage =
        error instanceof Error ? error.message : "Document upload failed.";

      setMessage(errorMessage);
      setIsError(true);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="page-stack documents-page">
      <header className="page-header">
        <div>
          <p className="eyebrow">Knowledge Base</p>

          <div className="title-with-info">
            <h1>Documents</h1>

            <InfoTooltip text="Add project requirements, user stories, acceptance criteria or API specifications. Uploaded content is indexed and used during test generation." />
          </div>

          <p className="page-description">
            Add the project documentation used by the retrieval pipeline when
            generating test cases.
          </p>
        </div>
      </header>

      <div className="page-help-wrapper">
        <button
          type="button"
          className="page-help-button"
          onClick={() => setShowPageHelp((current) => !current)}
          aria-expanded={showPageHelp}
        >
          <Info size={16} />
          How this page works
        </button>

        {showPageHelp && (
          <div className="page-help-panel">
            <p>
              Paste short requirements directly or upload an existing document.
              The system divides the content into searchable chunks and indexes
              it for retrieval.
            </p>
          </div>
        )}
      </div>

      <section className="card document-upload-card">
        <div className="card-heading-row">
          <div>
            <p className="eyebrow">Add documentation</p>
            <h2>Choose an upload method</h2>
            <p className="card-description">
              Both methods add content to the same indexed knowledge base.
            </p>
          </div>

          <span className="large-card-icon">
            <UploadCloud size={24} />
          </span>
        </div>

        <div
          className="upload-method-tabs"
          role="tablist"
          aria-label="Upload method"
        >
          <button
            type="button"
            role="tab"
            aria-selected={uploadMethod === "text"}
            className={
              uploadMethod === "text"
                ? "upload-method-tab active"
                : "upload-method-tab"
            }
            onClick={() => selectUploadMethod("text")}
          >
            <FileText size={18} />

            <span>
              <strong>Paste Text</strong>
              <small>Enter short requirements directly</small>
            </span>
          </button>

          <button
            type="button"
            role="tab"
            aria-selected={uploadMethod === "file"}
            className={
              uploadMethod === "file"
                ? "upload-method-tab active"
                : "upload-method-tab"
            }
            onClick={() => selectUploadMethod("file")}
          >
            <UploadCloud size={18} />

            <span>
              <strong>Upload File</strong>
              <small>Select an existing project document</small>
            </span>
          </button>
        </div>

        <form
          onSubmit={handleSubmit}
          className="document-form modern-document-form"
        >
          <div className="document-fields-grid">
            <label className="field-group">
              <span className="field-label">
                Document name
                <InfoTooltip text="A clear name used to identify this source in retrieval results and source references." />
              </span>

              <input
                value={name}
                onChange={(event) => setName(event.target.value)}
                placeholder="e.g. User Registration Requirements"
              />
            </label>

            <label className="field-group">
              <span className="field-label">
                Source type
                <InfoTooltip text="Optional category for the document, such as user_story, acceptance_criteria or api_spec." />
              </span>

              <input
                value={sourceType}
                onChange={(event) => setSourceType(event.target.value)}
                placeholder="e.g. user_story"
              />
            </label>
          </div>

          <label className="field-group">
            <span className="field-label">
              Format
              <InfoTooltip text="The document format used by the backend parser. File uploads automatically update this value from the selected extension." />
            </span>

            <select
              value={format}
              onChange={(event) => setFormat(event.target.value)}
            >
              {documentFormats.map((option) => (
                <option value={option} key={option}>
                  {option.toUpperCase()}
                </option>
              ))}
            </select>
          </label>

          {uploadMethod === "text" ? (
            <label className="field-group">
              <span className="field-label">
                Document content
                <InfoTooltip text="Paste requirements, user stories, acceptance criteria or API specifications." />
              </span>

              <textarea
                rows={11}
                value={content}
                onChange={(event) => setContent(event.target.value)}
                placeholder="Paste project requirements, user stories, acceptance criteria or API specifications here..."
              />

              <span className="field-hint">
                Short and structured content produces clearer retrieval results.
              </span>
            </label>
          ) : (
            <div className="field-group">
              <span className="field-label">
                Document file
                <InfoTooltip text="Supported file types: TXT, MD, JSON, YAML and YML." />
              </span>

              <div
                className={`file-drop-zone ${
                  isDragging ? "dragging" : ""
                } ${file ? "has-file" : ""}`}
                onDragOver={handleDragOver}
                onDragLeave={handleDragLeave}
                onDrop={handleDrop}
              >
                <input
                  ref={fileInputRef}
                  type="file"
                  className="file-input-hidden"
                  accept=".txt,.md,.json,.yaml,.yml"
                  onChange={handleFileChange}
                />

                {file ? (
                  <div className="selected-file">
                    <span className="selected-file-icon">
                      <FileText size={25} />
                    </span>

                    <div className="selected-file-details">
                      <strong>{file.name}</strong>
                      <span>
                        {(file.size / 1024).toFixed(1)} KB ·{" "}
                        {format.toUpperCase()}
                      </span>
                    </div>

                    <button
                      type="button"
                      className="remove-file-button"
                      aria-label="Remove selected file"
                      onClick={() => setSelectedFile(null)}
                    >
                      <X size={18} />
                    </button>
                  </div>
                ) : (
                  <>
                    <span className="drop-zone-icon">
                      <UploadCloud size={31} />
                    </span>

                    <strong>Drag and drop a document here</strong>

                    <p>or choose a supported file from your computer</p>

                    <button
                      type="button"
                      className="btn-secondary browse-file-button"
                      onClick={() => fileInputRef.current?.click()}
                    >
                      Browse files
                    </button>

                    <small>TXT, MD, JSON, YAML or YML</small>
                  </>
                )}
              </div>
            </div>
          )}

          {message && (
            <div
              className={
                isError ? "document-message error" : "document-message success"
              }
              role="status"
            >
              {isError ? <Info size={18} /> : <CheckCircle2 size={18} />}

              <span>{message}</span>
            </div>
          )}

          <button
            type="submit"
            className="btn-primary upload-document-button"
            disabled={loading}
          >
            {loading ? (
              <>
                <LoaderCircle className="button-spinner" size={18} />
                Uploading and indexing...
              </>
            ) : (
              <>
                <UploadCloud size={18} />
                Upload and index document
              </>
            )}
          </button>
        </form>
      </section>

      <section className="card indexed-documents-card">
        <div className="indexed-documents-header">
          <div>
            <p className="eyebrow">Knowledge sources</p>
            <h2>Indexed documents</h2>
            <p>Documents currently available to the retrieval pipeline.</p>
          </div>

          <span className="document-count-badge">
            {documents.length}{" "}
            {documents.length === 1 ? "document" : "documents"}
          </span>
        </div>

        {loadingDocuments && documents.length === 0 ? (
          <div className="empty-state">
            <LoaderCircle className="button-spinner" size={20} />
            Loading indexed documents...
          </div>
        ) : documents.length === 0 ? (
          <div className="empty-state documents-empty-state">
            <Layers3 size={29} />

            <strong>No indexed documents yet</strong>

            <span>
              Add your first requirement document to begin using RAG-based test
              generation.
            </span>
          </div>
        ) : (
          <div className="document-table-wrapper">
            <table className="doc-table">
              <thead>
                <tr>
                  <th>Document</th>
                  <th>Format</th>
                  <th>Source type</th>
                  <th>Chunks</th>
                  <th>Created</th>
                </tr>
              </thead>

              <tbody>
                {documents.map((doc) => (
                  <tr key={doc.id}>
                    <td>
                      <div className="document-name-cell">
                        <span className="document-file-icon">
                          <FileText size={17} />
                        </span>

                        <strong>{doc.name}</strong>
                      </div>
                    </td>

                    <td>
                      <span className="format-badge">
                        {doc.format.toUpperCase()}
                      </span>
                    </td>

                    <td>{doc.source_type || "Not specified"}</td>

                    <td>
                      {doc.chunk_count !== undefined ? doc.chunk_count : "..."}
                    </td>

                    <td>{new Date(doc.created_at).toLocaleString()}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
}

export default Documents;
