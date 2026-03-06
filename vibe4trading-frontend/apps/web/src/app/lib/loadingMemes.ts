import loadingMemeJson from "./loading_meme.json";

export type LoadingMemeStage = {
  stage: number;
  progress_percent: number;
  label: string;
  memes: string[];
};

type LoadingMemeConfig = {
  description: string;
  behavior: {
    total_duration_seconds: string;
    text_transition: string;
    progress_bar: string;
    on_complete: string;
  };
  stages: LoadingMemeStage[];
  implementation_notes: {
    how_to_use: string;
    code_example: string;
    stage_trigger: string;
    minimum_display_time: string;
  };
};

const loadingMemeConfig: LoadingMemeConfig = loadingMemeJson;

export const loadingStages = loadingMemeConfig.stages;
export const loadingBehavior = loadingMemeConfig.behavior;
export const MIN_STAGE_DISPLAY_MS = 1500;
export const TEXT_FADE_MS = 300;

export function resolveLoadingStageIndex(progressPercent: number, isTerminal: boolean) {
  const normalized = Math.max(0, Math.min(100, progressPercent));
  const lastNonTerminalIndex = Math.max(0, loadingStages.length - 2);
  const maxIndex = isTerminal ? loadingStages.length - 1 : lastNonTerminalIndex;

  let stageIndex = 0;
  for (let index = 0; index <= maxIndex; index += 1) {
    if (normalized >= loadingStages[index].progress_percent) {
      stageIndex = index;
    }
  }

  return stageIndex;
}

export function pickRandomMeme(stage: LoadingMemeStage, previousMeme?: string | null) {
  if (stage.memes.length === 0) return "";
  if (stage.memes.length === 1) return stage.memes[0];

  let next = stage.memes[Math.floor(Math.random() * stage.memes.length)];
  let attempts = 0;
  while (next === previousMeme && attempts < 4) {
    next = stage.memes[Math.floor(Math.random() * stage.memes.length)];
    attempts += 1;
  }
  return next;
}
