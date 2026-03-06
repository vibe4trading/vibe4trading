from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid5

_SCENARIO_NAMESPACE = UUID("6a38c29c-9c5c-4c6e-9d9f-1b6d1c4bbdf1")


@dataclass(frozen=True)
class ScenarioWindow:
    index: int
    label: str
    start: datetime
    end: datetime


@dataclass(frozen=True)
class ScenarioSet:
    key: str
    name: str
    description: str
    windows: list[ScenarioWindow]
    pace_seconds_per_base_tick: float = 2.0


def _default() -> ScenarioSet:
    base = datetime(2024, 1, 1, 0, 0, 0, tzinfo=UTC)
    windows: list[ScenarioWindow] = []

    # 10 short windows for fast tournament demos.
    window_hours = 12
    for i in range(10):
        start = base + timedelta(hours=i * window_hours)
        end = start + timedelta(hours=window_hours)
        windows.append(ScenarioWindow(index=i, label=f"Window {i + 1}", start=start, end=end))

    return ScenarioSet(
        key="default-v1",
        name="Default",
        description="10x 12h scenario windows (synthetic demo data). Early-checks disabled.",
        windows=windows,
        pace_seconds_per_base_tick=2.0,
    )


def _crypto_benchmark() -> ScenarioSet:
    base = datetime(2024, 1, 1, 0, 0, 0, tzinfo=UTC)
    windows: list[ScenarioWindow] = []
    window_hours = 168
    for i in range(10):
        start = base + timedelta(hours=i * 168)
        end = start + timedelta(hours=window_hours)
        windows.append(ScenarioWindow(index=i, label=f"Window {i + 1}", start=start, end=end))

    return ScenarioSet(
        key="crypto-benchmark-v1",
        name="Crypto Benchmark",
        description="10x 7d benchmark windows for 10-token tournament runs.",
        windows=windows,
        pace_seconds_per_base_tick=0.0,
    )


def list_scenario_sets() -> list[ScenarioSet]:
    return [_default(), _crypto_benchmark()]


def get_scenario_set(key: str) -> ScenarioSet | None:
    for s in list_scenario_sets():
        if s.key == key:
            return s
    return None


def scenario_dataset_id(
    *,
    scenario_set_key: str,
    category: str,
    market_id: str,
    start: datetime,
    end: datetime,
) -> UUID:
    # Deterministic UUID: submissions share identical datasets for fairness.
    seed = f"{scenario_set_key}|{category}|{market_id}|{start.isoformat()}|{end.isoformat()}"
    return uuid5(_SCENARIO_NAMESPACE, seed)
