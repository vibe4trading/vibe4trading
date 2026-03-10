import { Helmet } from "react-helmet-async";
import { Link } from "react-router-dom";

import { SEO } from "@/app/components/SEO";
import { AsciiDitherAnimation } from "./AsciiDitherAnimation";
import { Typewriter } from "./Typewriter";
import { useScrollReveal } from "./useScrollReveal";

const heroLabels = [
  {
    text: "WEB4 IS HERE.\nACTIVATING YOUR VIBE4TRADING.",
    className:
      "left-[4%] top-[9%] text-lg font-bold text-white drop-shadow-[0_0_18px_rgba(255,255,255,0.14)] md:text-3xl",
  },
  { text: "WHICH COIN?\nWHICH MODEL?", className: "right-[5%] top-[18%] text-xs text-zinc-300 md:text-base" },
  { text: "IS MY STRATEGY\nGOOD OR JUST LUCKY?", className: "left-[7%] top-[58%] text-xs text-zinc-300 md:text-sm" },
  { text: "TEST. REFINE. REPEAT.\nMODEL OPTIMIZATION.", className: "right-[6%] top-[50%] text-xs text-zinc-300 md:text-sm" },
  { text: "MAXIMIZE YOUR TRADES.", className: "right-[10%] bottom-[18%] text-xs text-zinc-300 md:text-base" },
];

const trials = [
  { id: "W01", name: "BYBIT HACK + DEATH CROSS", date: "FEB 2025", difficulty: "HARD" },
  { id: "W02", name: "WHITE HOUSE SUMMIT: SELL THE NEWS", date: "MAR 2025", difficulty: "MEDIUM" },
  { id: "W03", name: "90-DAY TARIFF PAUSE RALLY", date: "APR 2025", difficulty: "MEDIUM" },
  { id: "W04", name: "BTC DECOUPLES FROM GOLD", date: "APR 2025", difficulty: "EASY" },
  { id: "W05", name: "BORING CONSOLIDATION", date: "MAY 2025", difficulty: "EASY" },
  { id: "W06", name: "THE CALM BEFORE THE STORM", date: "SEP 2025", difficulty: "TRAP" },
  { id: "W07", name: "10/10 GREAT LIQUIDATION", date: "OCT 2025", difficulty: "CRASH" },
  { id: "W08", name: "INSTITUTIONAL RETREAT", date: "NOV 2025", difficulty: "HARD" },
  { id: "W09", name: "NEW YEAR FOG", date: "JAN 2026", difficulty: "FOG" },
  { id: "W10", name: "THE 2026 CRASH", date: "FEB 2026", difficulty: "CRASH" },
];

const steps = [
  {
    number: "01",
    title: "PICK YOUR AGENT",
    copy: "Choose the model, prompt, market, and risk settings you want to benchmark.",
  },
  {
    number: "02",
    title: "WE STRESS TEST IT",
    copy: "Run the same strategy through real historical windows with the same rules and data.",
  },
  {
    number: "03",
    title: "GET YOUR VERDICT",
    copy: "See returns, drawdown, hit rate, event-level behavior, and summary analysis.",
  },
  {
    number: "04",
    title: "OPTIMIZE AND COMPETE",
    copy: "Tune the prompt, rerun the trial, and compare yourself on the leaderboard.",
  },
];

const archetypes = [
  {
    title: "MEME HUNTER",
    name: "Ansem",
    copy: '"High-frequency short-term narrative chaser. Aggressive position sizing."',
  },
  {
    title: "DIAMOND HANDS",
    name: "Michael Saylor",
    copy: '"Low-frequency long holder. Disciplined and steady."',
  },
  {
    title: "MACRO SPECULATOR",
    name: "Arthur Hayes",
    copy: '"Bidirectional swing trader driven by macro rhythms."',
  },
  {
    title: "THE CONTRARIAN",
    name: "DonAlt",
    copy: '"Counter-consensus bottom fisher. Swing-oriented and patient."',
  },
  {
    title: "CONTRACT KING",
    name: "PickleCat (0xPickleCat)",
    copy: '"Futures-dominant medium-frequency trader. High leverage, high conviction."',
  },
  {
    title: "ON-CHAIN DETECTIVE",
    name: "ZachXBT",
    copy: '"Low leverage, risk-first approach. Defense over offense."',
  },
  {
    title: "FOMO WARRIOR",
    name: "Typical Retail",
    copy: '"Emotional buy-high sell-low pattern. Overtrades consistently."',
    dashed: true,
  },
  {
    title: "SUPERCYCLE BELIEVER",
    name: "Su Zhu (3AC)",
    copy: '"Perma-long with high leverage. Weak downside protection."',
    dashed: true,
  },
  {
    title: "DEGEN WHALE",
    name: "James Wynn",
    copy: '"Extreme leverage, concentrated bets. Massive volatility."',
    dashed: true,
  },
];

const team = [
  { name: "Jiarui Zhang", role: "AI Product Lead" },
  { name: "Grider Li", role: "Tech Lead" },
  { name: "Tiannan Zhao", role: "AI Product Strategy & Design" },
  { name: "Ruojia Ma", role: "Research Lead & Design" },
  { name: "Lyuyan Chen", role: "Engineer & Product Manager" },
  { name: "Jacky Yang", role: "Agentic Engineer" },
];

function fadeInClasses(visible: boolean) {
  return visible ? "animate-landing-fade-in-up opacity-100" : "opacity-0";
}

function HeroSection() {
  return (
    <section className="snap-start relative flex min-h-[calc(100vh-76px)] items-center justify-center overflow-hidden px-6 py-10">
      <div className="pointer-events-none absolute inset-0">
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_50%_22%,rgba(104,127,193,0.22),transparent_44%),radial-gradient(circle_at_50%_72%,rgba(255,255,255,0.05),transparent_30%)]" />
        <div className="absolute inset-0 opacity-35 [background-image:radial-gradient(circle,rgba(255,255,255,0.24)_1px,transparent_1px)] [background-size:28px_28px]" />
      </div>

      <div className="relative z-10 mx-auto flex w-full max-w-[1480px] flex-col items-center justify-center">
        <div className="relative flex min-h-[520px] w-full items-center justify-center md:min-h-[640px]">
          <AsciiDitherAnimation className="pointer-events-auto" />

          {heroLabels.map((label) => (
            <div
              key={label.text}
              className={`animate-landing-float absolute hidden max-w-[280px] whitespace-pre-line uppercase leading-tight tracking-[0.2em] md:block ${label.className}`}
            >
              {label.text}
            </div>
          ))}
        </div>

        <div className="mx-auto mt-2 max-w-4xl text-center uppercase">
          <div className="text-balance text-2xl font-bold tracking-[0.2em] md:hidden">
            WEB4 IS HERE. ACTIVATING YOUR VIBE4TRADING.
          </div>
          <div className="mt-3 text-sm tracking-[0.3em] text-zinc-400 md:hidden">
            TEST. REFINE. REPEAT.
          </div>

          <Link
            to="/arena"
            className="mt-10 inline-flex items-center justify-center border-2 border-white px-6 py-4 text-sm tracking-[0.25em] text-white transition-colors hover:bg-white hover:text-black md:px-12 md:text-lg"
          >
            START YOUR TRIAL
          </Link>
          <p className="mt-5 text-xs tracking-[0.32em] text-zinc-400 md:text-sm">
            10 EVENTS | 10 TOKENS | 1 SCORE | FREE
          </p>
        </div>
      </div>
    </section>
  );
}

function ProblemSection() {
  const { ref, visible } = useScrollReveal(0.2);

  return (
    <section
      ref={ref}
      className="snap-start flex min-h-[calc(100vh-76px)] items-center justify-center px-6 py-16"
    >
      <div className="max-w-4xl text-center uppercase">
        {[
          "IN THE WEB4 ERA,",
          "HUMANS DO NOT TRADE ANYMORE.",
          "AI AGENTS DO.",
          "",
          "BUT WITH DOZENS OF MODELS,",
          "HUNDREDS OF TOKENS,",
          "AND INFINITE CONFIGURATIONS,",
        ].map((line, index) =>
          line ? (
            <p
              key={line}
              className={`text-lg tracking-[0.16em] text-zinc-100 transition-all duration-700 md:text-3xl ${fadeInClasses(
                visible,
              )}`}
              style={{ animationDelay: `${index * 140}ms` }}
            >
              {line}
            </p>
          ) : (
            <div key={`spacer-${index}`} className="h-8 md:h-10" />
          ),
        )}

        <div className={`mt-10 text-xl tracking-[0.18em] md:text-4xl ${fadeInClasses(visible)}`}>
          {visible ? (
            <Typewriter
              text="HOW DO YOU KNOW IF YOUR STRATEGY ACTUALLY WORKS?"
              typingSpeed={45}
              startOnVisible={false}
            />
          ) : null}
        </div>
      </div>
    </section>
  );
}

function SolutionSection() {
  const { ref, visible } = useScrollReveal();

  return (
    <section
      ref={ref}
      className="snap-start flex min-h-[calc(100vh-76px)] items-center justify-center px-6 py-16"
    >
      <div className={`max-w-3xl ${fadeInClasses(visible)}`}>
        <h2 className="text-3xl uppercase tracking-[0.2em] text-white md:text-5xl">
          {visible ? (
            <Typewriter text="WE BENCHMARK IT FOR YOU." typingSpeed={55} startOnVisible={false} />
          ) : null}
        </h2>
        <p className="mt-8 text-base leading-8 tracking-[0.08em] text-zinc-300 md:text-lg">
          We run your agent through 10 real market regimes. Same rules. Same windows. No luck.
          Just performance.
        </p>
        <p className="mt-4 text-base leading-8 tracking-[0.08em] text-zinc-400 md:text-lg">
          See where your strategy survives, where it cracks, and how to improve the next pass.
        </p>
        <div className="mt-12 border-t border-white/20" />
      </div>
    </section>
  );
}

function HowItWorksSection() {
  const { ref, visible } = useScrollReveal();

  return (
    <section
      ref={ref}
      className="snap-start flex min-h-[calc(100vh-76px)] items-center justify-center px-6 py-20"
    >
      <div className="mx-auto w-full max-w-7xl">
        <h2 className={`text-center text-3xl uppercase tracking-[0.22em] text-white md:text-5xl ${fadeInClasses(visible)}`}>
          {visible ? <Typewriter text="HOW IT WORKS" typingSpeed={60} startOnVisible={false} /> : null}
        </h2>

        <div className="mt-14 grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          {steps.map((step, index) => (
            <article
              key={step.number}
              className={`border border-white/20 bg-white/[0.03] p-6 backdrop-blur-sm transition-all duration-700 hover:border-white/40 hover:bg-white/[0.05] ${fadeInClasses(
                visible,
              )}`}
              style={{ animationDelay: `${index * 120}ms` }}
            >
              <div className="text-5xl font-bold tracking-[0.12em] text-white">{step.number}</div>
              <h3 className="mt-5 text-lg uppercase tracking-[0.18em] text-white">{step.title}</h3>
              <p className="mt-4 text-sm leading-7 tracking-[0.08em] text-zinc-400">{step.copy}</p>
            </article>
          ))}
        </div>
      </div>
    </section>
  );
}

function TrialsSection() {
  const { ref, visible } = useScrollReveal();

  return (
    <section
      ref={ref}
      className="snap-start flex min-h-[calc(100vh-76px)] items-center justify-center px-6 py-20"
    >
      <div className="mx-auto w-full max-w-5xl">
        <h2 className={`text-3xl uppercase tracking-[0.22em] text-white md:text-5xl ${fadeInClasses(visible)}`}>
          {visible ? <Typewriter text="THE 10 TRIALS" typingSpeed={60} startOnVisible={false} /> : null}
        </h2>
        <p className={`mt-3 text-sm uppercase tracking-[0.28em] text-zinc-400 md:text-base ${fadeInClasses(visible)}`}>
          YOUR AGENT HAS TO SURVIVE ALL OF THEM.
        </p>

        <div className="mt-12 space-y-2">
          {trials.map((trial, index) => (
            <div
              key={trial.id}
              className={`grid grid-cols-[64px_1fr_88px] items-center gap-3 border-b border-white/10 py-3 text-xs uppercase tracking-[0.18em] text-zinc-300 md:grid-cols-[84px_1fr_120px_120px] md:text-sm ${fadeInClasses(
                visible,
              )}`}
              style={{ animationDelay: `${index * 90}ms` }}
            >
              <span className="text-zinc-500">{trial.id}</span>
              <span className="truncate text-zinc-100">{trial.name}</span>
              <span className="hidden text-right text-zinc-500 md:block">{trial.date}</span>
              <span className="text-right text-zinc-400">{trial.difficulty}</span>
            </div>
          ))}
        </div>

        <div className={`mt-12 space-y-2 text-sm leading-7 tracking-[0.1em] text-zinc-400 ${fadeInClasses(visible)}`}>
          <p>From flash crashes to boring chop.</p>
          <p>From liquidation cascades to slow institutional bleed.</p>
          <p>No safe windows. No cosmetic scoring.</p>
        </div>
      </div>
    </section>
  );
}

function ArchetypesSection() {
  const { ref, visible } = useScrollReveal();

  return (
    <section
      ref={ref}
      className="snap-start flex min-h-[calc(100vh-76px)] items-center justify-center px-6 py-20"
    >
      <div className="mx-auto w-full max-w-7xl">
        <h2 className={`text-center text-3xl uppercase tracking-[0.22em] text-white md:text-5xl ${fadeInClasses(visible)}`}>
          {visible ? (
            <Typewriter text="TRADER ARCHETYPES" typingSpeed={60} startOnVisible={false} />
          ) : null}
        </h2>
        <p className={`mt-3 text-center text-sm uppercase tracking-[0.28em] text-zinc-400 ${fadeInClasses(visible)}`}>
          WHICH ONE MATCHES YOUR STRATEGY?
        </p>

        <div className="mt-14 grid gap-4 lg:grid-cols-4">
          {archetypes.map((item, index) => (
            <article
              key={item.title}
              className={`flex min-h-[260px] flex-col border bg-white/[0.03] p-6 backdrop-blur-sm transition-all duration-700 ${
                item.dashed ? "border-dashed border-white/30" : "border-white/20"
              } ${fadeInClasses(visible)}`}
              style={{ animationDelay: `${index * 120}ms` }}
            >
              <h3 className="text-lg uppercase tracking-[0.18em] text-white">{item.title}</h3>
              <p className="mt-3 text-sm tracking-[0.08em] text-zinc-400">{item.name}</p>
              <p className="mt-auto pt-8 text-sm leading-7 tracking-[0.08em] text-zinc-300">{item.copy}</p>
            </article>
          ))}
        </div>

        <div className={`mx-auto mt-12 max-w-3xl text-center text-sm leading-7 tracking-[0.1em] text-zinc-400 ${fadeInClasses(visible)}`}>
          Your report maps behavior to recognizable trading archetypes, then points to the exact
          windows where that pattern helped or hurt.
        </div>
      </div>
    </section>
  );
}

function TeamSection() {
  const { ref, visible } = useScrollReveal();

  return (
    <section
      ref={ref}
      className="snap-start flex min-h-[calc(100vh-76px)] items-center justify-center px-6 py-20"
    >
      <div className="mx-auto w-full max-w-5xl">
        <h2 className={`text-center text-3xl uppercase tracking-[0.22em] text-white md:text-5xl ${fadeInClasses(visible)}`}>
          WHO WE ARE
        </h2>
        <p className={`mt-4 text-center text-sm tracking-[0.1em] text-zinc-400 ${fadeInClasses(visible)}`}>
          We build benchmark tooling for AI-native trading workflows.
        </p>

        <div className="mt-14 flex flex-wrap justify-center gap-x-16 gap-y-14">
          {team.map((member, index) => (
            <div
              key={member.name}
              className={`flex w-40 flex-col items-center gap-4 text-center ${fadeInClasses(visible)}`}
              style={{ animationDelay: `${index * 90}ms` }}
            >
              <div className="h-24 w-24 rounded-full border border-white/20 bg-white/[0.04]" />
              <div>
                <div className="text-sm tracking-[0.08em] text-zinc-400">
                  {member.role}
                </div>
                <div className="mt-2 text-lg tracking-[0.08em] text-white">{member.name}</div>
              </div>
            </div>
          ))}
        </div>

        <p className={`mt-14 text-center text-xs uppercase tracking-[0.3em] text-zinc-500 ${fadeInClasses(visible)}`}>
          Built for the Web4 trading era.
        </p>
      </div>
    </section>
  );
}

function FinalCtaSection() {
  const { ref, visible } = useScrollReveal();

  return (
    <section
      ref={ref}
      className="snap-start flex min-h-[calc(100vh-76px)] items-center justify-center px-6 py-20"
    >
      <div className={`mx-auto max-w-3xl text-center ${fadeInClasses(visible)}`}>
        <h2 className="text-3xl uppercase tracking-[0.22em] text-white md:text-6xl">
          {visible ? (
            <Typewriter text="READY TO FIND OUT?" typingSpeed={60} startOnVisible={false} />
          ) : null}
        </h2>
        <div className="mt-10 flex flex-col items-center gap-4 sm:flex-row sm:justify-center">
          <Link
            to="/arena"
            className="inline-flex min-w-[220px] items-center justify-center border-2 border-white px-8 py-4 text-sm uppercase tracking-[0.24em] text-white transition-colors hover:bg-white hover:text-black"
          >
            START YOUR TRIAL
          </Link>
          <Link
            to="/leaderboard"
            className="inline-flex min-w-[220px] items-center justify-center border border-white/30 bg-white/5 px-8 py-4 text-sm uppercase tracking-[0.24em] text-zinc-100 transition-colors hover:bg-white/10"
          >
            VIEW LEADERBOARD
          </Link>
        </div>
        <p className="mt-6 text-sm leading-7 tracking-[0.1em] text-zinc-400">
          Configure in minutes. Benchmark on real market windows. Iterate with evidence.
        </p>
      </div>
    </section>
  );
}

function FooterSection() {
  return (
    <footer className="border-t border-white/10 px-6 py-8 text-center">
      <p className="text-xs uppercase tracking-[0.32em] text-zinc-500">
        VIBE4TRADING | OPEN BENCHMARKS | 2026
      </p>
      <p className="mt-3 text-xs tracking-[0.2em] text-zinc-600">
        <Link to="/privacy" className="text-zinc-500 underline transition-colors hover:text-zinc-300">
          PRIVACY POLICY
        </Link>
      </p>
    </footer>
  );
}

export function LandingPage() {
  return (
    <main className="relative h-[calc(100vh-76px)] overflow-y-auto scroll-smooth snap-y snap-mandatory">
      <Helmet>
        <script type="application/ld+json">{JSON.stringify({
          "@context": "https://schema.org",
          "@type": "Organization",
          "name": "Vibe4Trading",
          "url": "https://vibe4trading.ai",
          "description": "AI crypto strategy benchmarking platform. Test if your AI trading strategy actually works.",
          "foundingDate": "2025"
        })}</script>
        <script type="application/ld+json">{JSON.stringify({
          "@context": "https://schema.org",
          "@type": "WebApplication",
          "name": "Vibe4Trading",
          "url": "https://vibe4trading.ai",
          "applicationCategory": "FinanceApplication",
          "operatingSystem": "Web",
          "description": "Benchmark LLM-powered trading agents across 10 real crypto market scenarios. Compare performance on a public leaderboard.",
          "offers": {
            "@type": "Offer",
            "price": "0",
            "priceCurrency": "USD"
          }
        })}</script>
      </Helmet>
      <SEO
        title="Vibe4Trading — AI Crypto Strategy Benchmarking"
        description="Test if your AI trading strategy actually works. Benchmark LLM agents across 10 real crypto market scenarios with fixed rules and data. Free."
        canonicalPath="/"
      />
      <div className="pointer-events-none absolute inset-0">
        <div className="absolute inset-0 bg-[linear-gradient(180deg,#020304_0%,#05070b_52%,#020203_100%)]" />
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_20%_15%,rgba(255,255,255,0.1),transparent_20%),radial-gradient(circle_at_78%_62%,rgba(255,255,255,0.08),transparent_18%),radial-gradient(circle_at_42%_78%,rgba(255,255,255,0.05),transparent_24%)]" />
      </div>

      <div className="relative z-10">
        <HeroSection />
        <ProblemSection />
        <SolutionSection />
        <HowItWorksSection />
        <TrialsSection />
        <ArchetypesSection />
        <TeamSection />
        <FinalCtaSection />
        <FooterSection />
      </div>
    </main>
  );
}
