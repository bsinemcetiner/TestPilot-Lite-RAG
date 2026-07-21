import { useEffect } from "react";

type DuplicateWarningModalProps = {
  isOpen: boolean;
  feature: string;
  createdAt: string;
  canViewPrevious: boolean;
  onCancel: () => void;
  onViewPrevious: () => void;
  onGenerateAnyway: () => void;
};

function DuplicateWarningModal({
  isOpen,
  feature,
  createdAt,
  canViewPrevious,
  onCancel,
  onViewPrevious,
  onGenerateAnyway,
}: DuplicateWarningModalProps) {
  useEffect(() => {
    if (!isOpen) return;

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        onCancel();
      }
    };

    document.addEventListener("keydown", handleKeyDown);
    document.body.style.overflow = "hidden";

    return () => {
      document.removeEventListener("keydown", handleKeyDown);
      document.body.style.overflow = "";
    };
  }, [isOpen, onCancel]);

  if (!isOpen) return null;

  return (
    <div className="modal-overlay" onMouseDown={onCancel} role="presentation">
      <div
        className="confirm-modal duplicate-modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby="duplicate-modal-title"
        onMouseDown={(event) => event.stopPropagation()}
      >
        <div className="confirm-modal-icon">⚠️</div>

        <div className="confirm-modal-content">
          <h2 id="duplicate-modal-title">Similar Generation Found</h2>

          <p>
            A generation with the same feature and description already exists in
            your history.
          </p>

          <div className="duplicate-details">
            <p>
              <strong>Feature:</strong> {feature}
            </p>

            <p>
              <strong>Generated:</strong> {new Date(createdAt).toLocaleString()}
            </p>
          </div>

          <p className="confirm-modal-warning">
            Generating again may produce similar test cases.
          </p>
        </div>

        <div className="duplicate-modal-actions">
          <button type="button" className="btn-secondary" onClick={onCancel}>
            Cancel
          </button>

          <button
            type="button"
            className="btn-secondary"
            onClick={onViewPrevious}
            disabled={!canViewPrevious}
            title={
              canViewPrevious
                ? "Open the previous result"
                : "Previous result data is unavailable"
            }
          >
            View Previous
          </button>

          <button
            type="button"
            className="btn-primary"
            onClick={onGenerateAnyway}
          >
            Generate Anyway
          </button>
        </div>
      </div>
    </div>
  );
}

export default DuplicateWarningModal;
