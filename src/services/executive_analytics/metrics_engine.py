"""Wave 8 (Executive Analytics): deterministic EVM-family metric
calculations over a Project's performance baseline + snapshot history.

Pure functions only -- no database access, no LLM call, no dependency on
`AdvisorFramework`/`AIContextEngine`. This is exactly the boundary the
Founder Mandate draws: "Nenhum LLM deve determinar silenciosamente...
financial variance... threshold... signal. Esses elementos devem ser
determinísticos."

Every metric is a `MetricValue`: either a real `Decimal` derived from real
inputs, or `None` with an explicit machine-readable `reason` -- never a
fabricated `0`, per Founder Decision "EVM Temporal Baseline"
(`docs/architecture/TECHNICAL-DESIGN-WAVE-8-EXECUTIVE-ANALYTICS.md`
Section 2.H).

`ev` (Earned Value) is deliberately not asserted as a certified metric --
it is derived from `Project.progress_percentage`, a manually-reported
field with no formal WBS/earned-value discipline behind it (Section 2.D).
Every caller (API response, frontend label) must present it as
"estimado a partir do progresso reportado", never as a certified EV.
"""
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

# Reason codes -- stable strings, safe to key UI copy/i18n off of.
NO_BASELINE_DEFINED = "no_baseline_defined"
BEFORE_BASELINE_START = "before_baseline_start"
AFTER_BASELINE_END = "after_baseline_end"
NO_SNAPSHOT_CAPTURED = "no_snapshot_captured"
ZERO_ACTUAL_COST = "zero_actual_cost"
ZERO_PLANNED_VALUE = "zero_planned_value"
ZERO_COST_PERFORMANCE_INDEX = "zero_cost_performance_index"


@dataclass(frozen=True)
class BaselinePoint:
    period_date: date
    planned_value: Decimal
    bac_reference: Decimal


@dataclass(frozen=True)
class PerformanceSnapshotPoint:
    snapshot_date: date
    actual_cost: Decimal
    progress_percentage: int


@dataclass(frozen=True)
class MetricValue:
    value: Decimal | None
    reason: str | None = None

    def __post_init__(self) -> None:
        if self.value is None and self.reason is None:
            raise ValueError("MetricValue with no value must carry a reason")
        if self.value is not None and self.reason is not None:
            raise ValueError("MetricValue with a value must not carry a reason")

    @staticmethod
    def present(value: Decimal) -> "MetricValue":
        return MetricValue(value=value)

    @staticmethod
    def na(reason: str) -> "MetricValue":
        return MetricValue(value=None, reason=reason)


@dataclass(frozen=True)
class EvmSummary:
    bac: MetricValue
    pv: MetricValue
    ev: MetricValue
    ac: MetricValue
    cpi: MetricValue
    spi: MetricValue
    cv: MetricValue
    sv: MetricValue
    eac: MetricValue
    etc: MetricValue
    vac: MetricValue


def _planned_value_at(baseline: list[BaselinePoint], as_of: date) -> MetricValue:
    if not baseline:
        return MetricValue.na(NO_BASELINE_DEFINED)
    ordered = sorted(baseline, key=lambda point: point.period_date)
    if as_of < ordered[0].period_date:
        return MetricValue.na(BEFORE_BASELINE_START)
    if as_of > ordered[-1].period_date:
        return MetricValue.na(AFTER_BASELINE_END)
    # Step function: the latest defined point at or before `as_of`. Never
    # interpolates a value between two authored points.
    applicable = [point for point in ordered if point.period_date <= as_of]
    return MetricValue.present(applicable[-1].planned_value)


def _latest_snapshot_at(
    snapshots: list[PerformanceSnapshotPoint], as_of: date
) -> PerformanceSnapshotPoint | None:
    applicable = [s for s in snapshots if s.snapshot_date <= as_of]
    if not applicable:
        return None
    return max(applicable, key=lambda s: s.snapshot_date)


def compute_evm_summary(
    baseline: list[BaselinePoint],
    snapshots: list[PerformanceSnapshotPoint],
    as_of: date,
) -> EvmSummary:
    """`baseline` should be the project's active (highest-version) baseline
    only -- callers resolve which version is active before calling this.
    `as_of` is normally today's date."""
    bac = (
        MetricValue.present(baseline[0].bac_reference)
        if baseline
        else MetricValue.na(NO_BASELINE_DEFINED)
    )
    pv = _planned_value_at(baseline, as_of)
    snapshot = _latest_snapshot_at(snapshots, as_of)

    if snapshot is None:
        ac = MetricValue.na(NO_SNAPSHOT_CAPTURED)
    else:
        ac = MetricValue.present(snapshot.actual_cost)

    if bac.value is None:
        ev = MetricValue.na(bac.reason)
    elif snapshot is None:
        ev = MetricValue.na(NO_SNAPSHOT_CAPTURED)
    else:
        ev = MetricValue.present(bac.value * Decimal(snapshot.progress_percentage) / Decimal(100))

    cpi = _ratio(ev, ac, ZERO_ACTUAL_COST)
    spi = _ratio(ev, pv, ZERO_PLANNED_VALUE)
    cv = _difference(ev, ac)
    sv = _difference(ev, pv)
    eac = _estimate_at_completion(ac, bac, ev, cpi)
    etc = _difference(eac, ac)
    vac = _difference(bac, eac)

    return EvmSummary(
        bac=bac, pv=pv, ev=ev, ac=ac, cpi=cpi, spi=spi, cv=cv, sv=sv, eac=eac, etc=etc, vac=vac
    )


def _ratio(numerator: MetricValue, denominator: MetricValue, zero_reason: str) -> MetricValue:
    if numerator.value is None:
        return MetricValue.na(numerator.reason)
    if denominator.value is None:
        return MetricValue.na(denominator.reason)
    if denominator.value == 0:
        return MetricValue.na(zero_reason)
    return MetricValue.present(numerator.value / denominator.value)


def _difference(minuend: MetricValue, subtrahend: MetricValue) -> MetricValue:
    if minuend.value is None:
        return MetricValue.na(minuend.reason)
    if subtrahend.value is None:
        return MetricValue.na(subtrahend.reason)
    return MetricValue.present(minuend.value - subtrahend.value)


def _estimate_at_completion(
    ac: MetricValue, bac: MetricValue, ev: MetricValue, cpi: MetricValue
) -> MetricValue:
    if ac.value is None:
        return MetricValue.na(ac.reason)
    if bac.value is None:
        return MetricValue.na(bac.reason)
    if ev.value is None:
        return MetricValue.na(ev.reason)
    if cpi.value is None:
        return MetricValue.na(cpi.reason)
    if cpi.value == 0:
        return MetricValue.na(ZERO_COST_PERFORMANCE_INDEX)
    return MetricValue.present(ac.value + (bac.value - ev.value) / cpi.value)
