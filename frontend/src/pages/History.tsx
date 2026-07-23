import { useEffect, useMemo, useState } from "react";
import { Clock3, Info, Search, Star, Trash2 } from "lucide-react";

import ConfirmModal from "../components/ConfirmModal";

import {
  GenerationHistoryItem,
  readGenerationHistory,
  sortGenerationHistory,
  writeGenerationHistory,
} from "../types/generationHistory";

type HistoryProps = {
  onOpenResults: (historyId?: string) => void;
};

function History({ onOpenResults }: HistoryProps) {
  const [history, setHistory] = useState<GenerationHistoryItem[]>([]);

  const [search, setSearch] = useState("");
  const [showPageHelp, setShowPageHelp] = useState(false);

  const [itemToDelete, setItemToDelete] =
    useState<GenerationHistoryItem | null>(null);

  useEffect(() => {
    setHistory(sortGenerationHistory(readGenerationHistory()));
  }, []);

  const filteredHistory = useMemo(() => {
    const normalizedSearch = search.trim().toLowerCase();

    return sortGenerationHistory(history).filter((item) => {
      if (!normalizedSearch) {
        return true;
      }

      return (
        item.feature.toLowerCase().includes(normalizedSearch) ||
        item.query.toLowerCase().includes(normalizedSearch) ||
        item.provider.toLowerCase().includes(normalizedSearch) ||
        item.outputFormat.toLowerCase().includes(normalizedSearch)
      );
    });
  }, [history, search]);

  const toggleFavorite = (id: string) => {
    const updatedHistory = history.map((item) =>
      item.id === id
        ? {
            ...item,
            isPinned: !item.isPinned,
          }
        : item,
    );

    setHistory(updatedHistory);
    writeGenerationHistory(updatedHistory);
  };

  const deleteHistoryItem = (id: string) => {
    const updatedHistory = history.filter((item) => item.id !== id);

    setHistory(updatedHistory);
    writeGenerationHistory(updatedHistory);
    setItemToDelete(null);
  };

  return (
    <div className="page-stack history-page">
      <header className="page-header">
        <div>
          <p className="eyebrow">Saved Generations</p>

          <div className="title-with-info">
            <h1>History</h1>
          </div>

          <p className="page-description">
            Search and manage test generations saved in this browser.
          </p>

          <div className="page-help-wrapper">
            <button
              type="button"
              className="page-help-button"
              aria-expanded={showPageHelp}
              onClick={() => setShowPageHelp((current) => !current)}
            >
              <Info size={16} />
              How history works
            </button>

            {showPageHelp && (
              <div className="page-help-panel">
                <p>
                  Generated results are stored locally in this browser. Select a
                  record to open it in Results, mark important generations as
                  favorites or remove records you no longer need.
                </p>
              </div>
            )}
          </div>
        </div>
      </header>

      <section className="card history-management-card">
        <div className="history-page-toolbar">
          <div>
            <p className="eyebrow">Generation Records</p>
            <h2>Saved History ({history.length})</h2>
          </div>

          <label className="history-modern-search">
            <Search size={17} />

            <input
              type="search"
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              placeholder="Search feature, query or provider..."
            />

            {search && (
              <button
                type="button"
                onClick={() => setSearch("")}
                aria-label="Clear search"
              >
                ×
              </button>
            )}
          </label>
        </div>

        {history.length === 0 ? (
          <div className="empty-state history-empty-state">
            <Clock3 size={31} />
            <strong>No generation history yet</strong>

            <span>Generate test cases to create your first saved result.</span>
          </div>
        ) : filteredHistory.length === 0 ? (
          <div className="empty-state">
            No saved generations match “{search}”.
          </div>
        ) : (
          <div className="modern-history-list">
            {filteredHistory.map((item) => (
              <article
                key={item.id}
                className="modern-history-card"
                role={item.response ? "button" : undefined}
                tabIndex={item.response ? 0 : -1}
                onClick={() => {
                  if (item.response) {
                    onOpenResults(item.id);
                  }
                }}
                onKeyDown={(event) => {
                  if (
                    item.response &&
                    (event.key === "Enter" || event.key === " ")
                  ) {
                    event.preventDefault();
                    onOpenResults(item.id);
                  }
                }}
              >
                <div className="modern-history-main">
                  <div className="modern-history-title">
                    <h3>{item.feature}</h3>

                    {item.isPinned && (
                      <span className="history-favorite-label">Favorite</span>
                    )}
                  </div>

                  <p>{item.query}</p>

                  <div className="modern-history-meta">
                    <span>{item.count} test cases</span>

                    <span>{item.outputFormat.toUpperCase()}</span>

                    <span>{item.provider.toUpperCase()}</span>

                    <span>{new Date(item.createdAt).toLocaleString()}</span>
                  </div>
                </div>

                <div className="modern-history-actions">
                  <button
                    type="button"
                    className={`modern-history-action favorite ${
                      item.isPinned ? "active" : ""
                    }`}
                    aria-label={
                      item.isPinned
                        ? "Remove from favorites"
                        : "Add to favorites"
                    }
                    onClick={(event) => {
                      event.stopPropagation();
                      toggleFavorite(item.id);
                    }}
                  >
                    <Star
                      size={18}
                      fill={item.isPinned ? "currentColor" : "none"}
                    />
                  </button>

                  <button
                    type="button"
                    className="modern-history-action delete"
                    aria-label="Delete generation"
                    onClick={(event) => {
                      event.stopPropagation();
                      setItemToDelete(item);
                    }}
                  >
                    <Trash2 size={18} />
                  </button>
                </div>
              </article>
            ))}
          </div>
        )}
      </section>

      <ConfirmModal
        isOpen={itemToDelete !== null}
        title="Delete Generation"
        message="Are you sure you want to remove this generation from your history?"
        warning="This action cannot be undone."
        confirmText="Delete"
        cancelText="Cancel"
        onCancel={() => setItemToDelete(null)}
        onConfirm={() => {
          if (itemToDelete) {
            deleteHistoryItem(itemToDelete.id);
          }
        }}
      />
    </div>
  );
}

export default History;
