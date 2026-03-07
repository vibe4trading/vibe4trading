export interface EventNode {
  t: string; // time
  a: string; // action
  l: string; // label/description
  r: string; // return
  p: number; // position in curve
}

export interface EventData {
  period: string;
  title: string;
  subtitle: string;
  difficulty: string;
  regime: string;
  edge: string;
  background: string;
  metrics: {
    ret: string;
    win: string;
    dd: string;
    pf: string;
    trades: string;
  };
  curve: number[];
  nodes: EventNode[];
}

export const storyCards: Record<string, EventData> = {
  W01: {
    period: "2025.02.21 – 02.28",
    title: "Bybit Hack + Death Cross",
    subtitle: "The first crisis of confidence after ETF approval",
    difficulty: "Hard",
    regime: "Panic Selloff",
    edge: "Weak",
    background:
      "Bybit suffered a $1.5B ETH theft — the second-largest hack in crypto history. BTC's 50-day MA crossed below its 200-day MA, forming a 'death cross.' The US imposed new tariffs on Canada and Mexico, fueling recession fears.",
    metrics: { ret: "-8.2%", win: "33%", dd: "-18.5%", pf: "0.6", trades: "7" },
    curve: [100, 97, 95, 92, 91, 89, 90, 88],
    nodes: [
      { t: "02/21 10:00", a: "Reduce long exposure", l: "Hack event impairs liquidity — capital preservation first", r: "-1.1%", p: 0 },
      { t: "02/24 03:00", a: "Attempt bounce long", l: "Oversold bounce signal appeared, but volume insufficient", r: "-2.4%", p: 2 },
      { t: "02/27 18:00", a: "Switch to defense", l: "Death cross confirmed — prioritize downtrend positioning", r: "+0.7%", p: 6 },
    ],
  },
  W02: {
    period: "2025.03.07 – 03.14",
    title: "WH Crypto Summit: Buy the Rumor, Sell the News",
    subtitle: "The first-ever White House crypto summit disappoints the market",
    difficulty: "Medium",
    regime: "News Repricing",
    edge: "Weak",
    background:
      "Trump hosted the first-ever White House cryptocurrency summit, declaring his intention to make America the 'crypto capital.' The market had already priced in the bullish narrative, pushing BTC above $90K. But the summit was all talk with no concrete legislative timeline — disappointment selling followed. A textbook 'buy the rumor, sell the news' event.",
    metrics: { ret: "-3.1%", win: "40%", dd: "-12.3%", pf: "0.8", trades: "5" },
    curve: [100, 101, 102, 100, 98, 97, 96, 97],
    nodes: [
      { t: "03/08 09:00", a: "Chase the rally", l: "Pre-summit optimism amplified — expecting policy delivery", r: "+0.9%", p: 2 },
      { t: "03/10 20:00", a: "Stop-loss exit", l: "Post-summit narrative collapsed — price-volume divergence widened", r: "-2.0%", p: 4 },
      { t: "03/13 12:00", a: "Light trial long", l: "Short-term oversold repair — small position bounce only", r: "-0.5%", p: 6 },
    ],
  },
  W03: {
    period: "2025.04.09 – 04.16",
    title: "90-Day Tariff Pause — Violent Rally",
    subtitle: "Nasdaq surges 12% in a single day, BTC follows",
    difficulty: "Medium",
    regime: "Policy Rebound",
    edge: "Strong",
    background:
      "In early April, Trump imposed 'reciprocal tariffs' globally, causing markets to plunge. On April 9 he abruptly announced a 90-day tariff suspension for most countries (excluding China). Nasdaq surged 12% — the second-largest single-day gain since 1950.",
    metrics: { ret: "+11.2%", win: "71%", dd: "-4.1%", pf: "2.1", trades: "7" },
    curve: [100, 101, 104, 106, 108, 110, 111, 112],
    nodes: [
      { t: "04/09 21:00", a: "Breakout long", l: "Policy inflection triggers risk-on sentiment", r: "+3.2%", p: 1 },
      { t: "04/11 14:00", a: "Add on pullback", l: "Pullback held key support — trend continuation", r: "+2.6%", p: 4 },
      { t: "04/15 19:00", a: "Scale out", l: "Rally too fast — protect against retracement eating profits", r: "+1.8%", p: 7 },
    ],
  },
  W04: {
    period: "2025.04.19 – 04.26",
    title: "BTC Decouples from Gold — Independent Surge",
    subtitle: "Capital rotates from gold to BTC, +12% in one week",
    difficulty: "Easy",
    regime: "Narrative Rotation",
    edge: "Strong",
    background:
      "Gold broke above $3,500 to a new ATH then pulled back. BTC began charting its own course — decoupling from gold, reducing correlation with Nasdaq. The 'BTC is digital gold' narrative reignited, with institutional capital flooding in through ETFs.",
    metrics: { ret: "+14.8%", win: "75%", dd: "-2.8%", pf: "2.8", trades: "4" },
    curve: [100, 102, 104, 108, 111, 113, 115, 114.8],
    nodes: [
      { t: "04/19 08:00", a: "Trend entry", l: "Decoupling signal appeared — macro narrative shifts to BTC independence", r: "+4.1%", p: 1 },
      { t: "04/22 06:00", a: "Add position", l: "ETF net inflows confirmed — price and volume in harmony", r: "+3.4%", p: 4 },
      { t: "04/25 23:00", a: "Lock in gains", l: "Short-term overheating — trim exposure to prevent drawdown", r: "+1.5%", p: 6 },
    ],
  },
  W05: {
    period: "2025.05.18 – 05.25",
    title: "Boring Chop — Are Your Hands Itching?",
    subtitle: "Pre-Bitcoin Conference lull, market shrinks to wait-and-see",
    difficulty: "Easy",
    regime: "Low Vol Chop",
    edge: "Average",
    background:
      "The Las Vegas Bitcoin Conference was approaching at month-end, with Trump expected to attend. Wait-and-see sentiment dominated, volume shrank, and BTC oscillated in a narrow range. This type of market is the most agonizing — doing nothing is the optimal strategy, but most people can't resist trading.",
    metrics: { ret: "+1.2%", win: "50%", dd: "-3.2%", pf: "1.1", trades: "2" },
    curve: [100, 100.4, 99.9, 100.6, 100.1, 101.1, 100.8, 101.2],
    nodes: [
      { t: "05/19 11:00", a: "Light trial long", l: "Bounce off range floor — tight stop-loss set", r: "+0.6%", p: 1 },
      { t: "05/22 17:00", a: "Flat, waiting", l: "Volatility contracting — risk/reward insufficient", r: "0.0%", p: 4 },
      { t: "05/24 09:00", a: "Small arb trade", l: "Range boundary reversal scalp — quick in, quick out", r: "+0.4%", p: 7 },
    ],
  },
  W06: {
    period: "2025.09.25 – 10.02",
    title: "Calm Before the Storm",
    subtitle: "BTC ranges near $120K while leverage piles up underwater",
    difficulty: "Medium",
    regime: "Leverage Build-up",
    edge: "Average",
    background:
      "BTC oscillated in a narrow $118K–$126K range, looking serene on the surface. But underneath, open interest hit a record $217B, and funding rates spiked from 10% to 30%. The market was a room packed with explosives — all it needed was a match. Eight days later, that match arrived.",
    metrics: { ret: "+3.4%", win: "60%", dd: "-5.1%", pf: "1.4", trades: "3" },
    curve: [100, 100.6, 101.2, 102.0, 101.4, 102.6, 103.1, 103.4],
    nodes: [
      { t: "09/26 13:00", a: "Low-leverage hold", l: "Trend intact but leverage risk rising — control exposure", r: "+1.0%", p: 2 },
      { t: "09/29 21:00", a: "Reduce size", l: "Funding rate overheated — avoid being caught in liquidation cascades", r: "+0.7%", p: 4 },
      { t: "10/01 18:00", a: "Short-term re-entry", l: "Range floor held with capital support", r: "+0.9%", p: 6 },
    ],
  },
  W07: {
    period: "2025.10.10 – 10.17",
    title: "The 10/10 Great Liquidation",
    subtitle: "Largest single-day liquidation in crypto history: $19B, 1.6M accounts",
    difficulty: "Extreme",
    regime: "Liquidation Cascade",
    edge: "Weak",
    background:
      "Trump announced 100% tariffs on China (130% total rate). BTC flash-crashed from $122K to $105K. $6.9B in positions were liquidated within 40 minutes — 86× normal speed. ETH dropped 21%, SOL dropped 40%, DOGE dropped 50%+. Total liquidations reached $19B across 1.6M accounts — multiples of the FTX collapse.",
    metrics: { ret: "-11.1%", win: "25%", dd: "-22.4%", pf: "0.4", trades: "9" },
    curve: [100, 99, 96, 92, 89, 90, 88, 88.9],
    nodes: [
      { t: "10/10 12:40", a: "Failed to stop-loss", l: "Misjudged as V-reversal — ignored liquidity gap", r: "-4.8%", p: 3 },
      { t: "10/10 13:20", a: "Sidelined post-liquidation", l: "System risk controls triggered — stopped adding", r: "-2.1%", p: 4 },
      { t: "10/12 08:00", a: "Small short trial", l: "Followed panic momentum — quick in, quick out", r: "+0.9%", p: 6 },
    ],
  },
  W08: {
    period: "2025.11.12 – 11.19",
    title: "10/10 Aftershock: The Capital Exodus",
    subtitle: "ETF single-month outflow hits $3.6B",
    difficulty: "Hard",
    regime: "Capital Flight",
    edge: "Weak",
    background:
      "One month after the 10/10 crash, the wounds hadn't healed. BTC spot ETFs saw $3.6B in monthly outflows — the largest since launch. BlackRock's IBIT recorded a single-day outflow of $523M, a record. MSCI published a consultation paper potentially removing MicroStrategy and similar companies from mainstream indices, forcing passive funds to sell an estimated $2.8–8.8B. The 'institutions are coming' narrative had become 'institutions are fleeing.'",
    metrics: { ret: "-5.6%", win: "38%", dd: "-14.7%", pf: "0.7", trades: "6" },
    curve: [100, 99, 97, 95, 94.5, 94, 94.2, 94.4],
    nodes: [
      { t: "11/13 08:00", a: "Light trial long", l: "Oversold bounce expected, but liquidity keeps draining", r: "-1.2%", p: 2 },
      { t: "11/16 15:00", a: "Stop-loss exit", l: "Capital outflows intensifying — exit promptly", r: "-1.9%", p: 4 },
      { t: "11/18 11:00", a: "Sidelined", l: "Waiting for stabilization signal — not chasing the short side", r: "+0.3%", p: 6 },
    ],
  },
  W09: {
    period: "2026.01.09 – 01.16",
    title: "New Year Fog: Bottom or False Bounce?",
    subtitle: "Fierce bull-bear divergence, MSCI decision imminent",
    difficulty: "Medium",
    regime: "Dead Cat Bounce",
    edge: "Average",
    background:
      "BTC ranged on thin volume between $83K–$96K. Bulls argued the 10/10 leverage had been flushed clean and a bottom was confirmed. Bears pointed to persistent ETF outflows and the MSCI decision due January 15. Direction was deeply uncertain. The week closed up ~5%, but nobody knew whether the next move was a rally or another leg down.",
    metrics: { ret: "+2.8%", win: "55%", dd: "-4.5%", pf: "1.3", trades: "3" },
    curve: [100, 101, 101.8, 102.4, 102.1, 102.6, 102.9, 102.8],
    nodes: [
      { t: "01/10 10:00", a: "Range trade", l: "Low-vol environment — scalping range boundaries", r: "+0.9%", p: 2 },
      { t: "01/13 14:00", a: "Reduce size", l: "Insufficient volume — limited bounce strength", r: "+0.7%", p: 4 },
      { t: "01/15 09:00", a: "Hold cash, wait", l: "Direction unclear — wait for breakout confirmation", r: "+0.5%", p: 6 },
    ],
  },
  W10: {
    period: "2026.01.30 – 02.06",
    title: "The 2026 Great Crash: BTC Breaks Below $70K",
    subtitle: "ETFs turn net sellers, basis trade collapses, full institutional retreat. Weekly drop exceeds 25%",
    difficulty: "Catastrophic",
    regime: "Market Collapse",
    edge: "Weak",
    background:
      "Microsoft's earnings miss dragged tech stocks down — BTC followed. ETFs flipped from net buying to net selling; they bought 46K BTC in Feb 2025, now they were selling in Feb 2026. Basis trade yields collapsed from 17% to below 5%, triggering massive hedge fund unwinds. Trump announced 15% global tariffs. US–Iran tensions escalated. BTC broke below its 365-day MA (first time since March 2022). Weekly RSI broke below 30. The week swung 36%, falling 25%+. This was not a flash crash with a V-shaped recovery — this was structural selling.",
    metrics: { ret: "-15.3%", win: "20%", dd: "-28.6%", pf: "0.3", trades: "11" },
    curve: [100, 96, 91, 85, 80, 78, 82, 84.7],
    nodes: [
      { t: "01/30 09:00", a: "Reduce exposure", l: "Risk signals stacking up — proactively lower exposure", r: "-2.1%", p: 1 },
      { t: "02/02 12:00", a: "Passive stop-loss", l: "All support levels broken — execute stop-loss discipline", r: "-5.7%", p: 3 },
      { t: "02/05 16:00", a: "Failed bottom catch", l: "Misjudged the bottom — liquidity continued to drain", r: "-3.2%", p: 5 },
    ],
  },
};

export const heatmapData = [
  { event: "W01", name: "Bybit Hack", mark: "weak", ret: "-8.2%", win: "33%", dd: "-18.5%", pf: "0.6", trades: 7 },
  { event: "W02", name: "Summit Sell", mark: "avg", ret: "-3.1%", win: "40%", dd: "-12.3%", pf: "0.8", trades: 5 },
  { event: "W03", name: "Tariff Rally", mark: "strong", ret: "+11.2%", win: "71%", dd: "-4.1%", pf: "2.1", trades: 7 },
  { event: "W04", name: "BTC Surge", mark: "strong", ret: "+14.8%", win: "75%", dd: "-2.8%", pf: "2.8", trades: 4 },
  { event: "W05", name: "Boring Chop", mark: "neutral", ret: "+1.2%", win: "50%", dd: "-3.2%", pf: "1.1", trades: 2 },
  { event: "W06", name: "Calm Storm", mark: "warn", ret: "+3.4%", win: "60%", dd: "-5.1%", pf: "1.4", trades: 3 },
  { event: "W07", name: "10/10 Crash", mark: "crash", ret: "-11.1%", win: "25%", dd: "-22.4%", pf: "0.4", trades: 9 },
  { event: "W08", name: "ETF Exodus", mark: "avg", ret: "-5.6%", win: "38%", dd: "-14.7%", pf: "0.7", trades: 6 },
  { event: "W09", name: "New Year Fog", mark: "neutral", ret: "+2.8%", win: "55%", dd: "-4.5%", pf: "1.3", trades: 3 },
  { event: "W10", name: "2026 Crash", mark: "crash", ret: "-15.3%", win: "20%", dd: "-28.6%", pf: "0.3", trades: 11 },
];
