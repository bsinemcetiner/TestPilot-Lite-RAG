import type { GenerationResponse } from "../api/apiClient";

export type GenerationHistoryItem = {
  id: string;
  feature: string;
  query: string;
  outputFormat: string;
  provider: string;
  count: number;
  createdAt: string;
  preview: string;
  isPinned?: boolean;
  response?: GenerationResponse;
};

export const HISTORY_STORAGE_KEY = "testpilot-history";

export function readGenerationHistory(): GenerationHistoryItem[] {
  const storedHistory = window.localStorage.getItem(HISTORY_STORAGE_KEY);

  if (!storedHistory) {
    return [];
  }

  try {
    const parsedHistory = JSON.parse(storedHistory);

    if (!Array.isArray(parsedHistory)) {
      return [];
    }

    return parsedHistory;
  } catch {
    window.localStorage.removeItem(HISTORY_STORAGE_KEY);
    return [];
  }
}

export function writeGenerationHistory(history: GenerationHistoryItem[]) {
  window.localStorage.setItem(HISTORY_STORAGE_KEY, JSON.stringify(history));
}

export function sortGenerationHistory(history: GenerationHistoryItem[]) {
  return [...history].sort((first, second) => {
    if (Boolean(first.isPinned) !== Boolean(second.isPinned)) {
      return Number(Boolean(second.isPinned)) - Number(Boolean(first.isPinned));
    }

    return (
      new Date(second.createdAt).getTime() - new Date(first.createdAt).getTime()
    );
  });
}
