export type SubmissionLoadingSnapshot = {
  marketId: string;
  modelKey: string;
  promptText: string;
  createdAt: number;
};

const SUBMISSION_LOADING_PREFIX = "v4t:arena-loading:";

function storageKey(submissionId: string) {
  return `${SUBMISSION_LOADING_PREFIX}${submissionId}`;
}

export function saveSubmissionLoadingSnapshot(
  submissionId: string,
  snapshot: Omit<SubmissionLoadingSnapshot, "createdAt">,
) {
  if (typeof window === "undefined") return;
  const payload: SubmissionLoadingSnapshot = {
    ...snapshot,
    createdAt: Date.now(),
  };
  window.sessionStorage.setItem(storageKey(submissionId), JSON.stringify(payload));
}

export function readSubmissionLoadingSnapshot(submissionId: string) {
  if (typeof window === "undefined") return null;

  const raw = window.sessionStorage.getItem(storageKey(submissionId));
  if (!raw) return null;

  try {
    const parsed = JSON.parse(raw) as Partial<SubmissionLoadingSnapshot>;
    if (
      typeof parsed.marketId === "string" &&
      typeof parsed.modelKey === "string" &&
      typeof parsed.promptText === "string" &&
      typeof parsed.createdAt === "number"
    ) {
      return parsed as SubmissionLoadingSnapshot;
    }
  } catch {
    return null;
  }

  return null;
}

export function clearSubmissionLoadingSnapshot(submissionId: string) {
  if (typeof window === "undefined") return;
  window.sessionStorage.removeItem(storageKey(submissionId));
}
