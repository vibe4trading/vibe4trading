import { Routes, Route, Link } from "react-router-dom";
import { RouteWrapper } from "@/app/components/RouteWrapper";

import HomePage from "@/app/page";
import ArenaPage from "@/app/arena/page";
import SubmissionDetailPage from "@/app/arena/submissions/[submissionId]/page";
import SubmissionLoadingPage from "@/app/arena/submissions/[submissionId]/loading/page";
import LeaderboardPage from "@/app/leaderboard/page";
import LivePage from "@/app/live/page";
import RunsPage from "@/app/runs/page";
import RunDetailPage from "@/app/runs/[runId]/page";
import RunWatchPage from "@/app/runs/[runId]/watch/page";
import AdminModelsPage from "@/app/admin/models/page";
import ContactPage from "@/app/contact/page";
import PrivacyPage from "@/app/privacy/page";

export default function App() {
  return (
    <RouteWrapper>
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/arena" element={<ArenaPage />} />
        <Route path="/arena/submissions/:submissionId" element={<SubmissionDetailPage />} />
        <Route path="/arena/submissions/:submissionId/loading" element={<SubmissionLoadingPage />} />
        <Route path="/leaderboard" element={<LeaderboardPage />} />
        <Route path="/live" element={<LivePage />} />
        <Route path="/runs" element={<RunsPage />} />
        <Route path="/runs/:runId" element={<RunDetailPage />} />
        <Route path="/runs/:runId/watch" element={<RunWatchPage />} />
        <Route path="/admin/models" element={<AdminModelsPage />} />
        <Route path="/contact" element={<ContactPage />} />
        <Route path="/privacy" element={<PrivacyPage />} />
        <Route path="*" element={
          <main className="mx-auto flex min-h-[60vh] max-w-xl flex-col items-center justify-center px-6 py-24 text-center">
            <h1 className="text-5xl font-bold tracking-tight text-white">404</h1>
            <p className="mt-4 text-lg text-zinc-400">Page not found</p>
            <Link to="/" className="mt-8 inline-block border border-zinc-600 px-6 py-3 text-sm font-medium uppercase tracking-widest text-zinc-300 transition-colors hover:border-white hover:text-white">
              Back to Home
            </Link>
          </main>
        } />
      </Routes>
    </RouteWrapper>
  );
}
