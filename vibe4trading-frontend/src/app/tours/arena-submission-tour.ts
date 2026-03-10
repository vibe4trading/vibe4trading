import type { DriveStep } from "driver.js";

export const arenaSubmissionSteps: DriveStep[] = [
  {
    element: '[data-tour="arena-pair-selector"]',
    popover: {
      title: "Choose Your Pair",
      description:
        "Select the trading pair for your benchmark. Each pair has its own historical scenario set.",
      side: "bottom",
    },
  },
  {
    element: '[data-tour="arena-model-selector"]',
    popover: {
      title: "Pick an AI Model",
      description:
        "Choose the LLM that will make trading decisions. Different models have different strengths.",
      side: "bottom",
    },
  },
  {
    element: '[data-tour="arena-prompt-mode"]',
    popover: {
      title: "Prompt Mode",
      description:
        "Beginner mode builds a prompt from dropdowns. Pro mode lets you write a custom strategy prompt.",
      side: "bottom",
    },
  },
  {
    element: '[data-tour="arena-beginner-dropdowns"]',
    popover: {
      title: "Configure Your Strategy",
      description:
        "Set trading style, time horizon, and risk tolerance. The prompt is generated automatically from these choices.",
      side: "top",
    },
  },
  {
    element: '[data-tour="arena-submit-button"]',
    popover: {
      title: "Launch Your Benchmark",
      description:
        "Submit your strategy to run across all historical scenario windows. Results appear in your trials list.",
      side: "top",
    },
  },
];
