"""TD-017 (V1 Post-Completion Technical Closure): Executive Signal Engine.

Backend port of the same deterministic algorithm already validated on the
frontend (`web/lib/domain/executive-signal.ts`, Wave 8) for the signals
that depend only on a single Project's own EVM history -- pure arithmetic
over `metrics_engine.py`'s already-computed `HistoryPoint`/`EvmSummary`,
zero LLM involvement, exactly the "IA não calcula" boundary this closure
must preserve.

A Signal is "a fact/condition derived deterministically from real data
that deserves executive attention" -- never a Decision, never a
Recommendation, never an action (mandate Section 12). Every field here
maps directly to Section 10's structured-evidence shape.

Out of scope for this closure (documented, not fabricated): portfolio-wide
concentration signals (portfolio_concentration/risk_concentration) require
cross-project aggregation not yet ported server-side -- see
`docs/architecture/TECHNICAL-DESIGN-TD-016-TD-017-POST-COMPLETION-CLOSURE.md`
Section 4.C.
"""
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from src.services.executive_analytics.metrics_engine import EvmSummary, HistoryPoint

COST_PERFORMANCE_DETERIORATING = "cost_performance_deteriorating"
SCHEDULE_PERFORMANCE_DETERIORATING = "schedule_performance_deteriorating"
RECOVERY_TREND = "recovery_trend"
FORECAST_DEVIATION = "forecast_deviation"

SEVERITY_INFO = "info"
SEVERITY_WARNING = "warning"
SEVERITY_CRITICAL = "critical"

FORECAST_DEVIATION_THRESHOLD = Decimal("0.1")
FORECAST_DEVIATION_CRITICAL_THRESHOLD = Decimal("0.25")


@dataclass(frozen=True)
class ExecutiveSignal:
    signal_type: str
    severity: str
    scope: str
    metric: str
    current_value: Decimal
    baseline_or_threshold: Decimal
    trend: str
    period: date
    evidence_reference: str
    provenance: str


def _ratio_series(
    history: list[HistoryPoint], numerator: str, denominator: str
) -> list[tuple[date, Decimal]]:
    series = []
    for point in history:
        num = getattr(point, numerator).value
        den = getattr(point, denominator).value
        if num is None or den is None or den == 0:
            continue
        series.append((point.as_of, num / den))
    return series


def _trend_signal(
    series: list[tuple[date, Decimal]],
    scope: str,
    metric: str,
    deteriorating_type: str,
    provenance: str,
) -> ExecutiveSignal | None:
    if len(series) < 2:
        return None
    previous_date, previous_ratio = series[-2]
    latest_date, latest_ratio = series[-1]
    if latest_ratio == previous_ratio:
        return None
    is_deteriorating = latest_ratio < previous_ratio
    severity = SEVERITY_CRITICAL if latest_ratio < 1 else SEVERITY_WARNING
    return ExecutiveSignal(
        signal_type=deteriorating_type if is_deteriorating else RECOVERY_TREND,
        severity=severity if is_deteriorating else SEVERITY_INFO,
        scope=scope,
        metric=metric,
        current_value=latest_ratio,
        baseline_or_threshold=previous_ratio,
        trend="down" if is_deteriorating else "up",
        period=latest_date,
        evidence_reference=(
            f"{metric} em {previous_date.isoformat()} ({previous_ratio:.2f}) -> "
            f"{latest_date.isoformat()} ({latest_ratio:.2f})"
        ),
        provenance=provenance,
    )


def derive_cost_performance_signal(
    history: list[HistoryPoint], scope: str
) -> ExecutiveSignal | None:
    """CPI (EV/AC) trend across real captured history -- needs at least 2
    points with both EV and AC present."""
    return _trend_signal(
        _ratio_series(history, "ev", "ac"),
        scope,
        "CPI",
        COST_PERFORMANCE_DETERIORATING,
        "metrics_engine.build_history_series",
    )


def derive_schedule_performance_signal(
    history: list[HistoryPoint], scope: str
) -> ExecutiveSignal | None:
    """SPI (EV/PV) trend across real captured history."""
    return _trend_signal(
        _ratio_series(history, "ev", "pv"),
        scope,
        "SPI",
        SCHEDULE_PERFORMANCE_DETERIORATING,
        "metrics_engine.build_history_series",
    )


def derive_forecast_deviation_signal(
    summary: EvmSummary, scope: str, as_of: date
) -> ExecutiveSignal | None:
    """Flags a material deviation between BAC and EAC -- requires both a
    real BAC (an authored baseline) and a real VAC (BAC - EAC, itself
    requiring EV/AC/CPI to all be real). Returns None otherwise, never a
    fabricated deviation."""
    bac = summary.bac.value
    vac = summary.vac.value
    if bac is None or vac is None or bac == 0:
        return None
    deviation_ratio = abs(vac) / bac
    if deviation_ratio < FORECAST_DEVIATION_THRESHOLD:
        return None
    severity = (
        SEVERITY_CRITICAL if deviation_ratio >= FORECAST_DEVIATION_CRITICAL_THRESHOLD else SEVERITY_WARNING
    )
    return ExecutiveSignal(
        signal_type=FORECAST_DEVIATION,
        severity=severity,
        scope=scope,
        metric="VAC / BAC",
        current_value=deviation_ratio * 100,
        baseline_or_threshold=FORECAST_DEVIATION_THRESHOLD * 100,
        trend="down" if vac < 0 else "up",
        period=as_of,
        evidence_reference=f"VAC de {vac:.2f} sobre BAC de {bac:.2f}",
        provenance="metrics_engine.compute_evm_summary",
    )
