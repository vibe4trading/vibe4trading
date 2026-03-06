"use client";

import * as React from "react";
import { useRouter } from "next/navigation";

import { NewRunModal } from "@/app/components/NewRunModal";
import { saveSubmissionLoadingSnapshot } from "@/app/lib/submissionLoading";
import { apiJson, ModelPublicOut } from "@/app/lib/v4t";

type NewRunContextValue = {
  openNewRun: () => void;
  markets: string[];
  models: ModelPublicOut[];
};

const NewRunContext = React.createContext<NewRunContextValue | null>(null);
const LEGACY_OUTPUT_FORMAT_BLOCK =
  '\n\nOutput format:\n{"schema_version":1,"targets":{"<market_id>":0.25},"confidence":0.6,"key_signals":["..."],"rationale":"..."}';

function firstSelectableModelKey(rows: ModelPublicOut[]) {
  return rows.find((row) => row.selectable)?.model_key ?? "";
}

export function NewRunProvider({ children }: { children: React.ReactNode }) {
  const router = useRouter();

  const [open, setOpen] = React.useState(false);
  const [markets, setMarkets] = React.useState<string[]>([]);
  const [models, setModels] = React.useState<ModelPublicOut[]>([]);
  const [marketsLoaded, setMarketsLoaded] = React.useState(false);
  const [modelsLoaded, setModelsLoaded] = React.useState(false);

  const [marketId, setMarketId] = React.useState("");
  const [modelKey, setModelKey] = React.useState("");
  const [promptText, setPromptText] = React.useState("");
  const [submitting, setSubmitting] = React.useState(false);
  const [submitError, setSubmitError] = React.useState<string | null>(null);

  React.useEffect(() => {
    apiJson<string[]>("/arena/markets")
      .then((rows) => {
        setMarkets(rows);
        setMarketId((current) => current || rows[0] || "");
      })
      .catch((e) => setSubmitError(e instanceof Error ? e.message : String(e)))
      .finally(() => setMarketsLoaded(true));

    apiJson<ModelPublicOut[]>("/models")
      .then((rows) => {
        setModels(rows);
        setModelKey((current) => {
          if (rows.some((row) => row.model_key === current && row.selectable)) return current;
          return firstSelectableModelKey(rows);
        });
      })
      .catch((e) => setSubmitError(e instanceof Error ? e.message : String(e)))
      .finally(() => setModelsLoaded(true));
  }, []);

  const openNewRun = React.useCallback(() => {
    setSubmitError(null);
    setPromptText((current) =>
      current.includes(LEGACY_OUTPUT_FORMAT_BLOCK)
        ? current.replace(LEGACY_OUTPUT_FORMAT_BLOCK, "").trim()
        : current,
    );
    setOpen(true);
  }, []);

  const closeNewRun = React.useCallback(() => {
    if (submitting) return;
    setOpen(false);
  }, [submitting]);

  const submitNewRun = React.useCallback(async () => {
    setSubmitting(true);
    setSubmitError(null);
    try {
      const body = await apiJson<{ submission_id: string }>("/arena/submissions", {
        method: "POST",
        body: {
          market_id: marketId,
          model_key: modelKey,
          prompt_text: promptText,
          visibility: "public",
        },
      });
      saveSubmissionLoadingSnapshot(body.submission_id, {
        marketId,
        modelKey,
        promptText,
      });
      setOpen(false);
      router.push(`/arena/submissions/${body.submission_id}/loading`);
    } catch (e) {
      setSubmitError(e instanceof Error ? e.message : String(e));
    } finally {
      setSubmitting(false);
    }
  }, [marketId, modelKey, promptText, router]);

  const contextValue = React.useMemo(
    () => ({ openNewRun, markets, models }),
    [openNewRun, markets, models],
  );

  return (
    <NewRunContext.Provider value={contextValue}>
      {children}
      <NewRunModal
        open={open}
        markets={markets}
        models={models}
        marketsLoaded={marketsLoaded}
        modelsLoaded={modelsLoaded}
        marketId={marketId}
        modelKey={modelKey}
        promptText={promptText}
        onChangeMarketId={setMarketId}
        onChangeModelKey={setModelKey}
        onChangePromptText={setPromptText}
        onClose={closeNewRun}
        onSubmit={submitNewRun}
        submitting={submitting}
        submitError={submitError}
      />
    </NewRunContext.Provider>
  );
}

export function useNewRunModal() {
  const context = React.useContext(NewRunContext);
  if (!context) {
    throw new Error("useNewRunModal must be used within a NewRunProvider");
  }
  return context;
}
