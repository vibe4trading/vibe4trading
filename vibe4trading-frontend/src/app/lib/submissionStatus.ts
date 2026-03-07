type SubmissionStatusInput = {
  status: string | null | undefined;
  startedAt?: string | null;
};

export type SubmissionStatusDisplay = {
  normalized: string;
  label: string;
  headline: string;
  detail: string;
  isQueued: boolean;
};

export function normalizeSubmissionStatus(status: string | null | undefined) {
  return status?.trim().toLowerCase() ?? "";
}

export function getSubmissionStatusDisplay({
  status,
  startedAt,
}: SubmissionStatusInput): SubmissionStatusDisplay {
  const normalized = normalizeSubmissionStatus(status);

  if (normalized === "pending" && !startedAt) {
    return {
      normalized,
      label: "Queued",
      headline: "Queued for execution",
      detail:
        "Your trial is safely in queue. It has not started yet, and this page will update as soon as a worker begins running it.",
      isQueued: true,
    };
  }

  if (normalized === "submitted") {
    return {
      normalized,
      label: "Submitting",
      headline: "Submitting trial",
      detail: "We are still locking in the submission details before the worker picks it up.",
      isQueued: false,
    };
  }

  if (normalized === "running") {
    return {
      normalized,
      label: "Running",
      headline: "Trial in progress",
      detail: "The worker has started replaying the historical windows. Progress updates will keep streaming in here.",
      isQueued: false,
    };
  }

  if (normalized === "finished") {
    return {
      normalized,
      label: "Finished",
      headline: "Historical Trial Verdict",
      detail: "The queued work is done and the full report is ready to inspect.",
      isQueued: false,
    };
  }

  if (normalized === "failed") {
    return {
      normalized,
      label: "Failed",
      headline: "Trial failed",
      detail: "The run left the queue but did not complete successfully.",
      isQueued: false,
    };
  }

  if (normalized === "cancelled") {
    return {
      normalized,
      label: "Cancelled",
      headline: "Trial cancelled",
      detail: "This submission will not continue running.",
      isQueued: false,
    };
  }

  return {
    normalized,
    label: normalized ? `${normalized.slice(0, 1).toUpperCase()}${normalized.slice(1)}` : "Pending",
    headline: "Trial status unavailable",
    detail: "The latest submission status has not loaded yet.",
    isQueued: false,
  };
}
