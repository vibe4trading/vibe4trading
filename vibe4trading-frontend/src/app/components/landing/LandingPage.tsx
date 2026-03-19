import { Helmet } from "react-helmet-async";
import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";

import { SEO } from "@/app/components/SEO";
import { usePrerenderReady } from "@/app/hooks/usePrerenderReady";
import { AsciiDitherAnimation } from "./AsciiDitherAnimation";
import { Typewriter } from "./Typewriter";
import { useScrollReveal } from "./useScrollReveal";

function fadeInClasses(visible: boolean) {
  return visible ? "animate-landing-fade-in-up opacity-100" : "opacity-0";
}

function HeroSection() {
  const { t } = useTranslation("landing");
  
  const heroLabels = [
    {
      text: t("hero.title"),
      className:
        "left-[4%] top-[9%] text-lg font-bold text-white drop-shadow-[0_0_18px_rgba(255,255,255,0.14)] md:text-3xl",
    },
    { text: t("hero.label1"), className: "right-[5%] top-[18%] text-xs text-zinc-300 md:text-base" },
    { text: t("hero.label2"), className: "left-[7%] top-[58%] text-xs text-zinc-300 md:text-sm" },
    { text: t("hero.label3"), className: "right-[6%] top-[50%] text-xs text-zinc-300 md:text-sm" },
    { text: t("hero.label4"), className: "right-[10%] bottom-[18%] text-xs text-zinc-300 md:text-base" },
  ];

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
            {t("hero.titleMobile")}
          </div>
          <div className="mt-3 text-sm tracking-[0.3em] text-zinc-400 md:hidden">
            {t("hero.subtitleMobile")}
          </div>

          <Link
            to="/arena"
            className="mt-10 inline-flex items-center justify-center border-2 border-white px-6 py-4 text-sm tracking-[0.25em] text-white transition-colors hover:bg-white hover:text-black md:px-12 md:text-lg"
          >
            {t("hero.cta")}
          </Link>
          <p className="mt-5 text-xs tracking-[0.32em] text-zinc-400 md:text-sm">
            {t("hero.features")}
          </p>
        </div>
      </div>
    </section>
  );
}

function ProblemSection() {
  const { ref, visible } = useScrollReveal(0.2);
  const { t } = useTranslation("landing");

  return (
    <section
      ref={ref}
      className="snap-start flex min-h-[calc(100vh-76px)] items-center justify-center px-6 py-16"
    >
      <div className="max-w-4xl text-center uppercase">
        {[
          t("problem.line1"),
          t("problem.line2"),
          t("problem.line3"),
          "",
          t("problem.line4"),
          t("problem.line5"),
          t("problem.line6"),
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
              text={t("problem.question")}
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
  const { t } = useTranslation("landing");

  return (
    <section
      ref={ref}
      className="snap-start flex min-h-[calc(100vh-76px)] items-center justify-center px-6 py-16"
    >
      <div className={`max-w-3xl ${fadeInClasses(visible)}`}>
        <h2 className="text-3xl uppercase tracking-[0.2em] text-white md:text-5xl">
          {visible ? (
            <Typewriter text={t("solution.heading")} typingSpeed={55} startOnVisible={false} />
          ) : null}
        </h2>
        <p className="mt-8 text-base leading-8 tracking-[0.08em] text-zinc-300 md:text-lg">
          {t("solution.paragraph1")}
        </p>
        <p className="mt-4 text-base leading-8 tracking-[0.08em] text-zinc-400 md:text-lg">
          {t("solution.paragraph2")}
        </p>
        <div className="mt-12 border-t border-white/20" />
      </div>
    </section>
  );
}

function HowItWorksSection() {
  const { ref, visible } = useScrollReveal();
  const { t } = useTranslation("landing");

  const steps = [
    {
      number: t("howItWorks.step1.number"),
      title: t("howItWorks.step1.title"),
      copy: t("howItWorks.step1.copy"),
    },
    {
      number: t("howItWorks.step2.number"),
      title: t("howItWorks.step2.title"),
      copy: t("howItWorks.step2.copy"),
    },
    {
      number: t("howItWorks.step3.number"),
      title: t("howItWorks.step3.title"),
      copy: t("howItWorks.step3.copy"),
    },
    {
      number: t("howItWorks.step4.number"),
      title: t("howItWorks.step4.title"),
      copy: t("howItWorks.step4.copy"),
    },
  ];

  return (
    <section
      ref={ref}
      className="snap-start flex min-h-[calc(100vh-76px)] items-center justify-center px-6 py-20"
    >
      <div className="mx-auto w-full max-w-7xl">
        <h2 className={`text-center text-3xl uppercase tracking-[0.22em] text-white md:text-5xl ${fadeInClasses(visible)}`}>
          {visible ? <Typewriter text={t("howItWorks.heading")} typingSpeed={60} startOnVisible={false} /> : null}
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
  const { t } = useTranslation("landing");

  const trials = [
    { id: t("trials.trial1.id"), name: t("trials.trial1.name"), date: t("trials.trial1.date"), difficulty: t("trials.trial1.difficulty") },
    { id: t("trials.trial2.id"), name: t("trials.trial2.name"), date: t("trials.trial2.date"), difficulty: t("trials.trial2.difficulty") },
    { id: t("trials.trial3.id"), name: t("trials.trial3.name"), date: t("trials.trial3.date"), difficulty: t("trials.trial3.difficulty") },
    { id: t("trials.trial4.id"), name: t("trials.trial4.name"), date: t("trials.trial4.date"), difficulty: t("trials.trial4.difficulty") },
    { id: t("trials.trial5.id"), name: t("trials.trial5.name"), date: t("trials.trial5.date"), difficulty: t("trials.trial5.difficulty") },
    { id: t("trials.trial6.id"), name: t("trials.trial6.name"), date: t("trials.trial6.date"), difficulty: t("trials.trial6.difficulty") },
    { id: t("trials.trial7.id"), name: t("trials.trial7.name"), date: t("trials.trial7.date"), difficulty: t("trials.trial7.difficulty") },
    { id: t("trials.trial8.id"), name: t("trials.trial8.name"), date: t("trials.trial8.date"), difficulty: t("trials.trial8.difficulty") },
    { id: t("trials.trial9.id"), name: t("trials.trial9.name"), date: t("trials.trial9.date"), difficulty: t("trials.trial9.difficulty") },
    { id: t("trials.trial10.id"), name: t("trials.trial10.name"), date: t("trials.trial10.date"), difficulty: t("trials.trial10.difficulty") },
  ];

  return (
    <section
      ref={ref}
      className="snap-start flex min-h-[calc(100vh-76px)] items-center justify-center px-6 py-20"
    >
      <div className="mx-auto w-full max-w-5xl">
        <h2 className={`text-3xl uppercase tracking-[0.22em] text-white md:text-5xl ${fadeInClasses(visible)}`}>
          {visible ? <Typewriter text={t("trials.heading")} typingSpeed={60} startOnVisible={false} /> : null}
        </h2>
        <p className={`mt-3 text-sm uppercase tracking-[0.28em] text-zinc-400 md:text-base ${fadeInClasses(visible)}`}>
          {t("trials.subtitle")}
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
          <p>{t("trials.footer1")}</p>
          <p>{t("trials.footer2")}</p>
          <p>{t("trials.footer3")}</p>
        </div>
      </div>
    </section>
  );
}

function ArchetypesSection() {
  const { ref, visible } = useScrollReveal();
  const { t } = useTranslation("landing");

  const archetypes = [
    {
      title: t("archetypes.memeHunter.title"),
      name: t("archetypes.memeHunter.name"),
      copy: t("archetypes.memeHunter.copy"),
    },
    {
      title: t("archetypes.diamondHands.title"),
      name: t("archetypes.diamondHands.name"),
      copy: t("archetypes.diamondHands.copy"),
    },
    {
      title: t("archetypes.macroSpeculator.title"),
      name: t("archetypes.macroSpeculator.name"),
      copy: t("archetypes.macroSpeculator.copy"),
    },
    {
      title: t("archetypes.contrarian.title"),
      name: t("archetypes.contrarian.name"),
      copy: t("archetypes.contrarian.copy"),
    },
    {
      title: t("archetypes.contractKing.title"),
      name: t("archetypes.contractKing.name"),
      copy: t("archetypes.contractKing.copy"),
    },
    {
      title: t("archetypes.onChainDetective.title"),
      name: t("archetypes.onChainDetective.name"),
      copy: t("archetypes.onChainDetective.copy"),
    },
    {
      title: t("archetypes.fomoWarrior.title"),
      name: t("archetypes.fomoWarrior.name"),
      copy: t("archetypes.fomoWarrior.copy"),
      dashed: true,
    },
    {
      title: t("archetypes.supercycleBeliever.title"),
      name: t("archetypes.supercycleBeliever.name"),
      copy: t("archetypes.supercycleBeliever.copy"),
      dashed: true,
    },
    {
      title: t("archetypes.degenWhale.title"),
      name: t("archetypes.degenWhale.name"),
      copy: t("archetypes.degenWhale.copy"),
      dashed: true,
    },
  ];

  return (
    <section
      ref={ref}
      className="snap-start flex min-h-[calc(100vh-76px)] items-center justify-center px-6 py-20"
    >
      <div className="mx-auto w-full max-w-7xl">
        <h2 className={`text-center text-3xl uppercase tracking-[0.22em] text-white md:text-5xl ${fadeInClasses(visible)}`}>
          {visible ? (
            <Typewriter text={t("archetypes.heading")} typingSpeed={60} startOnVisible={false} />
          ) : null}
        </h2>
        <p className={`mt-3 text-center text-sm uppercase tracking-[0.28em] text-zinc-400 ${fadeInClasses(visible)}`}>
          {t("archetypes.subtitle")}
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
          {t("archetypes.footer")}
        </div>
      </div>
    </section>
  );
}

function TeamSection() {
  const { ref, visible } = useScrollReveal();
  const { t } = useTranslation("landing");

  const team = [
    { name: t("team.member1.name"), role: t("team.member1.role") },
    { name: t("team.member2.name"), role: t("team.member2.role") },
    { name: t("team.member3.name"), role: t("team.member3.role") },
    { name: t("team.member4.name"), role: t("team.member4.role") },
    { name: t("team.member5.name"), role: t("team.member5.role") },
    { name: t("team.member6.name"), role: t("team.member6.role") },
  ];

  return (
    <section
      ref={ref}
      className="snap-start flex min-h-[calc(100vh-76px)] items-center justify-center px-6 py-20"
    >
      <div className="mx-auto w-full max-w-5xl">
        <h2 className={`text-center text-3xl uppercase tracking-[0.22em] text-white md:text-5xl ${fadeInClasses(visible)}`}>
          {t("team.heading")}
        </h2>
        <p className={`mt-4 text-center text-sm tracking-[0.1em] text-zinc-400 ${fadeInClasses(visible)}`}>
          {t("team.subtitle")}
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
          {t("team.footer")}
        </p>
      </div>
    </section>
  );
}

function FinalCtaSection() {
  const { ref, visible } = useScrollReveal();
  const { t } = useTranslation("landing");

  return (
    <section
      ref={ref}
      className="snap-start flex min-h-[calc(100vh-76px)] items-center justify-center px-6 py-20"
    >
      <div className={`mx-auto max-w-3xl text-center ${fadeInClasses(visible)}`}>
        <h2 className="text-3xl uppercase tracking-[0.22em] text-white md:text-6xl">
          {visible ? (
            <Typewriter text={t("finalCta.heading")} typingSpeed={60} startOnVisible={false} />
          ) : null}
        </h2>
        <div className="mt-10 flex flex-col items-center gap-4 sm:flex-row sm:justify-center">
          <Link
            to="/arena"
            className="inline-flex min-w-[220px] items-center justify-center border-2 border-white px-8 py-4 text-sm uppercase tracking-[0.24em] text-white transition-colors hover:bg-white hover:text-black"
          >
            {t("finalCta.startTrial")}
          </Link>
          <Link
            to="/leaderboard"
            className="inline-flex min-w-[220px] items-center justify-center border border-white/30 bg-white/5 px-8 py-4 text-sm uppercase tracking-[0.24em] text-zinc-100 transition-colors hover:bg-white/10"
          >
            {t("finalCta.viewLeaderboard")}
          </Link>
        </div>
        <p className="mt-6 text-sm leading-7 tracking-[0.1em] text-zinc-400">
          {t("finalCta.description")}
        </p>
      </div>
    </section>
  );
}

function FooterSection() {
  const { t } = useTranslation("landing");

  return (
    <footer className="border-t border-white/10 px-6 py-8 text-center">
      <p className="text-xs uppercase tracking-[0.32em] text-zinc-500">
        {t("footer.copyright")}
      </p>
      <p className="mt-3 text-xs tracking-[0.2em] text-zinc-600">
        <Link to="/privacy" className="text-zinc-500 underline transition-colors hover:text-zinc-300">
          {t("footer.privacyPolicy")}
        </Link>
      </p>
    </footer>
  );
}

export function LandingPage() {
  usePrerenderReady(true);

  return (
    <main className="relative h-[calc(100vh-76px)] overflow-y-auto scroll-smooth snap-y snap-mandatory">
      <Helmet>
        <script type="application/ld+json">{JSON.stringify({
          "@context": "https://schema.org",
          "@type": "Organization",
          "name": "Vibe4Trading",
          "url": "https://vibe4trading.ai",
          "description": "Web4 AI trading agent benchmark platform. Where Web3 crypto markets meet AI-powered autonomous trading strategies.",
          "foundingDate": "2025"
        })}</script>
        <script type="application/ld+json">{JSON.stringify({
          "@context": "https://schema.org",
          "@type": "WebApplication",
          "name": "Vibe4Trading",
          "url": "https://vibe4trading.ai",
          "applicationCategory": "FinanceApplication",
          "operatingSystem": "Web",
          "description": "The first Web4 benchmark platform. Stress-test LLM-powered trading agents across 10 real crypto market scenarios. Web3 + AI = Web4.",
          "offers": {
            "@type": "Offer",
            "price": "0",
            "priceCurrency": "USD"
          }
        })}</script>
      </Helmet>
      <SEO
        title="Vibe4Trading — Web4 AI Trading Agent Benchmarks"
        description="Web4 = Web3 + AI. Benchmark autonomous AI trading agents across 10 real crypto market scenarios. Stress-test LLM strategies with fixed rules and data. Free."
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
