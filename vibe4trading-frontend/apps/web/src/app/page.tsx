import Link from "next/link";

export default function Home() {
  return (
    <main className="home-main">
      <section className="home-stage">
        <p className="home-copy home-copy-main">
          WEB4 IS HERE.<br />PREPARE YOUR VIBE4TRADING._
        </p>
        <p className="home-copy home-copy-right-top">
          WHICH COIN?<br />WHICH MODEL?_
        </p>
        <p className="home-copy home-copy-left-mid">
          IS MY STRATEGY<br />GOOD OR JUST LUCKY?_
        </p>
        <p className="home-copy home-copy-right-mid">
          TEST. REFINE. REPEAT.<br />MODEL OPTIMIZATION._
        </p>

        <div className="home-helmet-wrap" aria-hidden="true">
          <div className="home-helmet">SPARTAN<br />CORE</div>
        </div>

        <Link href="/arena" className="home-start-btn">
          START YOUR EXAM →
        </Link>
        <div className="home-subline">
          10 EVENTS · 10 TOKENS · 1 SCORE · FREE
        </div>

        <div className="home-bottom-actions">
          <Link href="/live" className="home-bottom-btn text-center block" style={{ textDecoration: 'none' }}>
            MY RUNS
          </Link>
          <Link href="/runs/new" className="home-bottom-btn primary text-center block" style={{ textDecoration: 'none' }}>
            NEW RUN
          </Link>
        </div>
      </section>
    </main>
  );
}
