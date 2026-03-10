import type { DriveStep } from "driver.js";

export const leaderboardSteps: DriveStep[] = [
  {
    element: '[data-tour="leaderboard-filters"]',
    popover: {
      title: "Filter Rankings",
      description:
        "Narrow results by model or trading pair. The leaderboard updates live as you change filters.",
      side: "bottom",
    },
  },
  {
    element: '[data-tour="leaderboard-kpi-cards"]',
    popover: {
      title: "Key Performance Metrics",
      description:
        "Top-line stats at a glance \u2014 filtered count, best PnL, Sharpe ratio, and maximum drawdown.",
      side: "bottom",
    },
  },
  {
    element: '[data-tour="leaderboard-table"]',
    popover: {
      title: "Strategy Rankings",
      description:
        "Click any row to see detailed stats. Strategies are ranked by composite PnL across historical scenarios.",
      side: "top",
    },
  },
  {
    element: '[data-tour="leaderboard-side-panel"]',
    popover: {
      title: "Strategy Details",
      description:
        "Dive into per-window returns, risk metrics, and ranking rules for the selected strategy.",
      side: "left",
    },
  },
];
