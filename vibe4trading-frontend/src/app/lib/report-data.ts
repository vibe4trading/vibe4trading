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
    title: "Bybit被盗 + 死亡交叉",
    subtitle: "ETF获批后的第一场信心危机",
    difficulty: "Hard",
    regime: "Panic Selloff",
    edge: "Weak",
    background:
      "Bybit遭受$15亿ETH被盗，加密史第二大黑客事件。BTC 50日均线下穿200日均线形成死亡交叉。美国对加墨加征关税，经济衰退恐惧蔓延。",
    metrics: { ret: "-8.2%", win: "33%", dd: "-18.5%", pf: "0.6", trades: "7" },
    curve: [100, 97, 95, 92, 91, 89, 90, 88],
    nodes: [
      { t: "02/21 10:00", a: "减仓多头", l: "黑客事件冲击流动性，优先保护本金", r: "-1.1%", p: 0 },
      { t: "02/24 03:00", a: "尝试反弹多单", l: "超跌反弹信号出现，但成交量不足", r: "-2.4%", p: 2 },
      { t: "02/27 18:00", a: "切换防守", l: "死亡交叉确认，下行趋势优先", r: "+0.7%", p: 6 },
    ],
  },
  W02: {
    period: "2025.03.07 – 03.14",
    title: "白宫加密峰会：买预期，卖事实",
    subtitle: "史上首次白宫加密峰会，结果让市场失望",
    difficulty: "Medium",
    regime: "News Repricing",
    edge: "Weak",
    background:
      "Trump在白宫举办首次加密货币峰会，市场会前已提前交易利好。峰会内容偏务虚，缺乏具体立法时间表，失望性抛售出现。",
    metrics: { ret: "-3.1%", win: "40%", dd: "-12.3%", pf: "0.8", trades: "5" },
    curve: [100, 101, 102, 100, 98, 97, 96, 97],
    nodes: [
      { t: "03/08 09:00", a: "追多", l: "会前乐观情绪放大，预期政策落地", r: "+0.9%", p: 2 },
      { t: "03/10 20:00", a: "止损离场", l: "会后叙事落空，量价背离扩大", r: "-2.0%", p: 4 },
      { t: "03/13 12:00", a: "低仓位试多", l: "短线超跌修复，仅做小仓位反弹", r: "-0.5%", p: 6 },
    ],
  },
  W03: {
    period: "2025.04.09 – 04.16",
    title: "关税暂停90天，暴力反弹",
    subtitle: "纳斯达克单日涨12%，BTC跟涨",
    difficulty: "Medium",
    regime: "Policy Rebound",
    edge: "Strong",
    background:
      "4月初市场因全球关税消息下挫，4月9日突然宣布对大部分国家暂停关税90天。风险资产快速修复，BTC与美股同步反弹。",
    metrics: { ret: "+11.2%", win: "71%", dd: "-4.1%", pf: "2.1", trades: "7" },
    curve: [100, 101, 104, 106, 108, 110, 111, 112],
    nodes: [
      { t: "04/09 21:00", a: "突破追多", l: "政策拐点触发风险偏好回归", r: "+3.2%", p: 1 },
      { t: "04/11 14:00", a: "回踩加仓", l: "回踩不破关键支撑，趋势延续", r: "+2.6%", p: 4 },
      { t: "04/15 19:00", a: "分批止盈", l: "涨幅过快，防止高位回撤吞噬利润", r: "+1.8%", p: 7 },
    ],
  },
  W04: {
    period: "2025.04.19 – 04.26",
    title: "BTC与黄金脱钩，独立暴涨",
    subtitle: "资金从黄金轮动到BTC，一周+12%",
    difficulty: "Easy",
    regime: "Narrative Rotation",
    edge: "Strong",
    background:
      "黄金创高后回落，BTC开始走独立行情，与纳指相关性降低。数字黄金叙事被重新点燃，机构资金通过ETF集中流入。",
    metrics: { ret: "+14.8%", win: "75%", dd: "-2.8%", pf: "2.8", trades: "4" },
    curve: [100, 102, 104, 108, 111, 113, 115, 114.8],
    nodes: [
      { t: "04/19 08:00", a: "趋势开仓", l: "脱钩信号出现，宏观叙事切换到BTC独立行情", r: "+4.1%", p: 1 },
      { t: "04/22 06:00", a: "加仓", l: "ETF净流入确认，量价共振", r: "+3.4%", p: 4 },
      { t: "04/25 23:00", a: "锁定收益", l: "短期过热，提前收缩仓位防回撤", r: "+1.5%", p: 6 },
    ],
  },
  W05: {
    period: "2025.05.18 – 05.25",
    title: "无聊的横盘，你的手痒了吗？",
    subtitle: "Bitcoin Conference前夕，市场缩量观望",
    difficulty: "Easy",
    regime: "Low Vol Chop",
    edge: "Average",
    background:
      "会议前市场观望情绪浓厚，成交量萎缩，BTC窄幅震荡。此阶段交易频率过高通常会被噪音吞噬。",
    metrics: { ret: "+1.2%", win: "50%", dd: "-3.2%", pf: "1.1", trades: "2" },
    curve: [100, 100.4, 99.9, 100.6, 100.1, 101.1, 100.8, 101.2],
    nodes: [
      { t: "05/19 11:00", a: "轻仓试多", l: "区间下沿反弹，设置紧止损", r: "+0.6%", p: 1 },
      { t: "05/22 17:00", a: "空仓等待", l: "波动收敛，风险收益比不足", r: "0.0%", p: 4 },
      { t: "05/24 09:00", a: "小仓位套利", l: "利用区间边界做反转，快进快出", r: "+0.4%", p: 7 },
    ],
  },
  W06: {
    period: "2025.09.25 – 10.02",
    title: "暴风雨前的宁静",
    subtitle: "BTC在$120K附近横盘，杠杆在水下疯狂堆积",
    difficulty: "Medium",
    regime: "Leverage Build-up",
    edge: "Average",
    background:
      "BTC在$118K-$126K窄幅震荡，表面平静但合约未平仓量创纪录，资金费率快速抬升。市场处于高压临界点。",
    metrics: { ret: "+3.4%", win: "60%", dd: "-5.1%", pf: "1.4", trades: "3" },
    curve: [100, 100.6, 101.2, 102.0, 101.4, 102.6, 103.1, 103.4],
    nodes: [
      { t: "09/26 13:00", a: "低杠杆持有", l: "趋势未破但杠杆风险上升，控制风险暴露", r: "+1.0%", p: 2 },
      { t: "09/29 21:00", a: "减仓", l: "资金费率过热，避免被挤压清算链波及", r: "+0.7%", p: 4 },
      { t: "10/01 18:00", a: "短线回补", l: "区间下沿资金承接有效", r: "+0.9%", p: 6 },
    ],
  },
  W07: {
    period: "2025.10.10 – 10.17",
    title: "10/10 大清算",
    subtitle: "加密史上最大单日爆仓事件：$190亿，160万个账户",
    difficulty: "Extreme",
    regime: "Liquidation Cascade",
    edge: "Weak",
    background:
      "Trump宣布对华100%关税（总税率130%），BTC从$122K闪崩至$105K。40分钟内$69亿仓位被清算，市场深度失衡。",
    metrics: { ret: "-11.1%", win: "25%", dd: "-22.4%", pf: "0.4", trades: "9" },
    curve: [100, 99, 96, 92, 89, 90, 88, 88.9],
    nodes: [
      { t: "10/10 12:40", a: "未及时止损", l: "误判为V反，忽视流动性断层", r: "-4.8%", p: 3 },
      { t: "10/10 13:20", a: "强平后观望", l: "系统风控触发，停止加仓", r: "-2.1%", p: 4 },
      { t: "10/12 08:00", a: "小仓试空", l: "顺势跟随恐慌，快进快出", r: "+0.9%", p: 6 },
    ],
  },
  W08: {
    period: "2025.10.20 – 10.27",
    title: "恐慌蔓延，ETF资金外流",
    subtitle: "连续7日资金净流出，BTC破位下行",
    difficulty: "Hard",
    regime: "Capital Flight",
    edge: "Weak",
    background:
      "10/10清算余震未平，投资者信心受挫。机构通过ETF持续赎回，现货市场承压。山寨币流动性枯竭，恐慌指数攀升。",
    metrics: { ret: "-5.6%", win: "38%", dd: "-14.7%", pf: "0.7", trades: "6" },
    curve: [100, 99, 97, 95, 94.5, 94, 94.2, 94.4],
    nodes: [
      { t: "10/21 08:00", a: "轻仓试多", l: "超跌反弹预期，但流动性持续萎缩", r: "-1.2%", p: 2 },
      { t: "10/24 15:00", a: "止损", l: "资金面持续恶化，及时离场", r: "-1.9%", p: 4 },
      { t: "10/26 11:00", a: "观望", l: "等待企稳信号，不追空", r: "+0.3%", p: 6 },
    ],
  },
  W09: {
    period: "2026.01.02 – 01.09",
    title: "新年迷雾，反弹还是陷阱？",
    subtitle: "短暂修复后再次承压",
    difficulty: "Medium",
    regime: "Dead Cat Bounce",
    edge: "Average",
    background:
      "新年假期成交量低迷，市场在$102K-$106K窄幅震荡。宏观不确定性仍存，投资者观望情绪浓厚。",
    metrics: { ret: "+2.8%", win: "55%", dd: "-4.5%", pf: "1.3", trades: "3" },
    curve: [100, 101, 101.8, 102.4, 102.1, 102.6, 102.9, 102.8],
    nodes: [
      { t: "01/03 10:00", a: "区间交易", l: "低波环境，利用区间边界套利", r: "+0.9%", p: 2 },
      { t: "01/06 14:00", a: "减仓", l: "量能不足，反弹力度有限", r: "+0.7%", p: 4 },
      { t: "01/08 09:00", a: "持币观望", l: "方向不明，等待突破确认", r: "+0.5%", p: 6 },
    ],
  },
  W10: {
    period: "2026.02.28 – 03.07",
    title: "2026 大崩盘",
    subtitle: "市场结构性崩溃，BTC腰斩",
    difficulty: "Catastrophic",
    regime: "Market Collapse",
    edge: "Weak",
    background:
      "全球宏观风险集中爆发，主权债务危机、银行系统流动性枯竭、加密监管收紧三重打击。BTC从$105K暴跌至$68K，市场进入恐慌模式。",
    metrics: { ret: "-15.3%", win: "20%", dd: "-28.6%", pf: "0.3", trades: "11" },
    curve: [100, 96, 91, 85, 80, 78, 82, 84.7],
    nodes: [
      { t: "02/28 09:00", a: "减仓", l: "风险信号密集，主动降低敞口", r: "-2.1%", p: 1 },
      { t: "03/02 12:00", a: "被动止损", l: "跌破所有支撑，执行止损纪律", r: "-5.7%", p: 3 },
      { t: "03/05 16:00", a: "抄底失败", l: "误判底部，流动性持续枯竭", r: "-3.2%", p: 5 },
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
