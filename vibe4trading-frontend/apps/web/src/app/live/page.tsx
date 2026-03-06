"use client";

export default function LivePage() {
  return (
    <main className="flex flex-col items-center justify-center min-h-[70vh] gap-6 select-none">
      <style jsx>{`
        .scene {
          position: relative;
          width: 320px;
          height: 120px;
          overflow: hidden;
          border: 3px solid var(--line);
          background:
            repeating-linear-gradient(
              90deg,
              transparent 0px,
              transparent 7px,
              rgba(0,0,0,0.03) 7px,
              rgba(0,0,0,0.03) 8px
            ),
            linear-gradient(180deg, #c8dbbe 0%, #a4c490 60%, #7a9a64 60%, #6b8a55 100%);
          image-rendering: pixelated;
        }

        /* ground line */
        .scene::after {
          content: "";
          position: absolute;
          bottom: 28px;
          left: 0;
          right: 0;
          height: 3px;
          background: #4a5a3a;
        }

        /* pixel rabbit */
        .rabbit {
          position: absolute;
          bottom: 31px;
          image-rendering: pixelated;
          animation: rabbitRun 6s linear infinite;
        }

        .rabbit-body {
          width: 20px;
          height: 14px;
          background: #f0f0f0;
          border: 2px solid #333;
          border-radius: 2px;
          position: relative;
        }

        .rabbit-body::before {
          content: "";
          position: absolute;
          top: -10px;
          right: 2px;
          width: 4px;
          height: 10px;
          background: #f0f0f0;
          border: 2px solid #333;
          border-bottom: none;
          animation: earWiggle 0.3s steps(2) infinite;
        }

        .rabbit-body::after {
          content: "";
          position: absolute;
          top: -10px;
          right: 8px;
          width: 4px;
          height: 8px;
          background: #f0f0f0;
          border: 2px solid #333;
          border-bottom: none;
          animation: earWiggle 0.3s steps(2) infinite 0.15s;
        }

        .rabbit-eye {
          position: absolute;
          top: 3px;
          right: 3px;
          width: 3px;
          height: 3px;
          background: #c0392b;
          border-radius: 0;
        }

        .rabbit-tail {
          position: absolute;
          top: 2px;
          left: -6px;
          width: 6px;
          height: 6px;
          background: #fff;
          border: 2px solid #333;
          border-radius: 50%;
        }

        .rabbit-legs {
          position: absolute;
          bottom: -6px;
          right: 4px;
          width: 4px;
          height: 6px;
          background: #333;
          animation: legMove 0.2s steps(2) infinite;
        }

        .rabbit-legs::after {
          content: "";
          position: absolute;
          left: 8px;
          width: 4px;
          height: 6px;
          background: #333;
          animation: legMove 0.2s steps(2) infinite 0.1s;
        }

        /* pixel alice */
        .alice {
          position: absolute;
          bottom: 31px;
          image-rendering: pixelated;
          animation: aliceRun 6s linear infinite;
        }

        .alice-head {
          width: 12px;
          height: 12px;
          background: #fdd9b5;
          border: 2px solid #333;
          position: absolute;
          top: 0;
          left: 4px;
          border-radius: 1px;
        }

        .alice-head::before {
          content: "";
          position: absolute;
          top: -4px;
          left: -2px;
          width: 16px;
          height: 6px;
          background: #f5d442;
          border: 2px solid #333;
          border-bottom: none;
          border-radius: 2px 2px 0 0;
        }

        .alice-head::after {
          content: "";
          position: absolute;
          top: 4px;
          left: 7px;
          width: 2px;
          height: 2px;
          background: #333;
        }

        .alice-hair-side {
          position: absolute;
          top: 4px;
          left: 1px;
          width: 4px;
          height: 16px;
          background: #f5d442;
          border: 1px solid #c9a830;
        }

        .alice-hair-side-r {
          left: auto;
          right: -1px;
        }

        .alice-dress {
          position: absolute;
          top: 12px;
          left: 2px;
          width: 16px;
          height: 14px;
          background: #5b9bd5;
          border: 2px solid #333;
          border-radius: 0 0 2px 2px;
        }

        .alice-dress::before {
          content: "";
          position: absolute;
          top: 0;
          left: 2px;
          right: 2px;
          height: 4px;
          background: #fff;
          border-bottom: 1px solid #ccc;
        }

        .alice-legs {
          position: absolute;
          bottom: -8px;
          left: 6px;
          width: 3px;
          height: 8px;
          background: #333;
          animation: legMove 0.25s steps(2) infinite;
        }

        .alice-legs::after {
          content: "";
          position: absolute;
          left: 6px;
          width: 3px;
          height: 8px;
          background: #333;
          animation: legMove 0.25s steps(2) infinite 0.12s;
        }

        .alice-arm {
          position: absolute;
          top: 14px;
          right: -4px;
          width: 4px;
          height: 10px;
          background: #fdd9b5;
          border: 1px solid #333;
          transform-origin: top center;
          animation: armReach 0.4s steps(3) infinite;
        }

        @keyframes rabbitRun {
          0% { left: 280px; }
          85% { left: 40px; }
          86% { left: 40px; bottom: 31px; }
          90% { bottom: 55px; left: 20px; }
          94% { bottom: 31px; left: 0px; }
          100% { left: -30px; }
        }

        @keyframes aliceRun {
          0% { left: 220px; }
          80% { left: 20px; }
          90% { left: 10px; }
          100% { left: -40px; }
        }

        @keyframes earWiggle {
          0% { transform: rotate(0deg); }
          100% { transform: rotate(8deg); }
        }

        @keyframes legMove {
          0% { height: 6px; }
          100% { height: 3px; }
        }

        @keyframes armReach {
          0% { transform: rotate(0deg); }
          50% { transform: rotate(-30deg); }
          100% { transform: rotate(0deg); }
        }

        /* little ground details */
        .grass {
          position: absolute;
          bottom: 28px;
          width: 4px;
          height: 6px;
          background: #5a7a44;
        }

        /* pocket watch floating */
        .watch {
          position: absolute;
          top: 20px;
          width: 10px;
          height: 10px;
          border: 2px solid #c9a830;
          border-radius: 50%;
          background: #f5e6a3;
          animation: watchBob 6s linear infinite;
        }

        .watch::before {
          content: "";
          position: absolute;
          top: -5px;
          left: 3px;
          width: 2px;
          height: 4px;
          background: #c9a830;
        }

        @keyframes watchBob {
          0% { left: 270px; transform: rotate(0deg); }
          85% { left: 30px; transform: rotate(720deg); }
          100% { left: -20px; transform: rotate(900deg); }
        }

        .label {
          font-size: 10px;
          letter-spacing: 1px;
          text-transform: uppercase;
          color: #4a5a3a;
          position: absolute;
          bottom: 6px;
          left: 0;
          right: 0;
          text-align: center;
        }
      `}</style>

      <div className="scene">
        {/* grass tufts */}
        <div className="grass" style={{ left: 30 }} />
        <div className="grass" style={{ left: 80 }} />
        <div className="grass" style={{ left: 140 }} />
        <div className="grass" style={{ left: 200 }} />
        <div className="grass" style={{ left: 260 }} />

        {/* pocket watch */}
        <div className="watch" />

        {/* rabbit */}
        <div className="rabbit">
          <div className="rabbit-body">
            <div className="rabbit-eye" />
            <div className="rabbit-tail" />
            <div className="rabbit-legs" />
          </div>
        </div>

        {/* alice */}
        <div className="alice">
          <div className="alice-head" />
          <div className="alice-hair-side" />
          <div className="alice-hair-side alice-hair-side-r" />
          <div className="alice-dress" />
          <div className="alice-arm" />
          <div className="alice-legs" />
        </div>

        <div className="label">down the rabbit hole...</div>
      </div>

      <div className="flex flex-col items-center gap-2">
        <h1 className="text-3xl font-bold tracking-wide">LIVE TRADING</h1>
        <p className="text-lg text-[var(--muted)]">Coming soon</p>
        <p className="text-sm text-[var(--muted)] mt-1 max-w-xs text-center">
          We&apos;re chasing this feature down the rabbit hole. Stay tuned.
        </p>
      </div>
    </main>
  );
}
