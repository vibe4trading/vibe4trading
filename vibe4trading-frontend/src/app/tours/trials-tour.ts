import type { DriveStep } from "driver.js";

export const trialsSteps: DriveStep[] = [
  {
    element: '[data-tour="trials-new-run-button"]',
    popover: {
      title: "Start a New Trial",
      description:
        "Click here to submit a new strategy to the arena. Pick a coin, model, and prompt — the platform benchmarks it across historical scenarios.",
      side: "bottom",
    },
  },
  {
    element: '[data-tour="trials-submissions-list"]',
    popover: {
      title: "Your Submissions",
      description:
        "All your arena submissions appear here. Click any row to view the full benchmark report with metrics across all scenario windows.",
      side: "top",
    },
  },
  {
    element: '[data-tour="trials-quota-chip"]',
    popover: {
      title: "Daily Quota",
      description:
        "Track your remaining runs for today. The quota resets at midnight UTC.",
      side: "bottom",
    },
  },
  {
    element: '[data-tour="trials-leaderboard-link"]',
    popover: {
      title: "Check the Leaderboard",
      description:
        "See how your strategies rank against others. Sorted by composite PnL with Sharpe and drawdown tiebreakers.",
      side: "bottom",
    },
  },
];
