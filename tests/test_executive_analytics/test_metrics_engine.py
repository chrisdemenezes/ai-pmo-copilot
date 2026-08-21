from datetime import date
from decimal import Decimal

import pytest

from src.services.executive_analytics.metrics_engine import (
    AFTER_BASELINE_END,
    BEFORE_BASELINE_START,
    NO_BASELINE_DEFINED,
    NO_SNAPSHOT_CAPTURED,
    ZERO_ACTUAL_COST,
    ZERO_PLANNED_VALUE,
    BaselinePoint,
    PerformanceSnapshotPoint,
    compute_evm_summary,
)


def _baseline() -> list[BaselinePoint]:
    bac = Decimal("100000.00")
    return [
        BaselinePoint(date(2026, 1, 1), Decimal("0.00"), bac),
        BaselinePoint(date(2026, 2, 1), Decimal("25000.00"), bac),
        BaselinePoint(date(2026, 3, 1), Decimal("50000.00"), bac),
        BaselinePoint(date(2026, 4, 1), Decimal("100000.00"), bac),
    ]


class TestNoBaselineDefined:
    def test_every_metric_is_na_with_no_baseline_defined_when_baseline_is_empty(self):
        snapshots = [PerformanceSnapshotPoint(date(2026, 2, 1), Decimal("20000.00"), 20)]

        summary = compute_evm_summary([], snapshots, as_of=date(2026, 2, 1))

        assert summary.bac.value is None and summary.bac.reason == NO_BASELINE_DEFINED
        assert summary.pv.value is None and summary.pv.reason == NO_BASELINE_DEFINED
        assert summary.ev.value is None and summary.ev.reason == NO_BASELINE_DEFINED
        assert summary.cpi.value is None
        assert summary.spi.value is None
        assert summary.eac.value is None


class TestNoSnapshotCaptured:
    def test_ac_and_ev_are_na_but_pv_and_bac_remain_real_when_no_snapshot_exists(self):
        summary = compute_evm_summary(_baseline(), [], as_of=date(2026, 2, 1))

        assert summary.bac.value == Decimal("100000.00")
        assert summary.pv.value == Decimal("25000.00")
        assert summary.ac.value is None and summary.ac.reason == NO_SNAPSHOT_CAPTURED
        assert summary.ev.value is None and summary.ev.reason == NO_SNAPSHOT_CAPTURED
        assert summary.cpi.value is None
        assert summary.spi.value is None


class TestFullDataAvailable:
    def test_computes_all_evm_metrics_from_real_baseline_and_snapshot(self):
        snapshots = [PerformanceSnapshotPoint(date(2026, 2, 1), Decimal("20000.00"), 20)]

        summary = compute_evm_summary(_baseline(), snapshots, as_of=date(2026, 2, 1))

        assert summary.bac.value == Decimal("100000.00")
        assert summary.pv.value == Decimal("25000.00")
        assert summary.ev.value == Decimal("20000.00")
        assert summary.ac.value == Decimal("20000.00")
        assert summary.cpi.value == Decimal(1)
        assert summary.spi.value == Decimal("0.8")
        assert summary.cv.value == Decimal("0.00")
        assert summary.sv.value == Decimal("-5000.00")
        assert summary.eac.value == Decimal("100000.00")
        assert summary.etc.value == Decimal("80000.00")
        assert summary.vac.value == Decimal("0.00")


class TestStepFunctionNeverInterpolates:
    def test_pv_uses_latest_defined_point_at_or_before_as_of_never_interpolated(self):
        summary = compute_evm_summary(_baseline(), [], as_of=date(2026, 2, 15))

        # 2026-02-15 falls between the 02-01 (25000) and 03-01 (50000)
        # authored points -- must snap back to 02-01's real value, never a
        # linearly interpolated 37500.
        assert summary.pv.value == Decimal("25000.00")


class TestOutOfRangeAsOf:
    def test_before_baseline_start_is_na_not_zero(self):
        summary = compute_evm_summary(_baseline(), [], as_of=date(2025, 12, 1))
        assert summary.pv.value is None
        assert summary.pv.reason == BEFORE_BASELINE_START

    def test_after_baseline_end_is_na_not_extrapolated(self):
        summary = compute_evm_summary(_baseline(), [], as_of=date(2026, 5, 1))
        assert summary.pv.value is None
        assert summary.pv.reason == AFTER_BASELINE_END


class TestZeroDivisionNeverCrashesAndIsExplicitNA:
    def test_zero_actual_cost_makes_cpi_na_not_a_crash(self):
        snapshots = [PerformanceSnapshotPoint(date(2026, 2, 1), Decimal("0.00"), 20)]

        summary = compute_evm_summary(_baseline(), snapshots, as_of=date(2026, 2, 1))

        assert summary.ac.value == Decimal("0.00")
        assert summary.cpi.value is None
        assert summary.cpi.reason == ZERO_ACTUAL_COST

    def test_zero_planned_value_makes_spi_na_not_a_crash(self):
        snapshots = [PerformanceSnapshotPoint(date(2026, 1, 1), Decimal("500.00"), 0)]

        summary = compute_evm_summary(_baseline(), snapshots, as_of=date(2026, 1, 1))

        assert summary.pv.value == Decimal("0.00")
        assert summary.spi.value is None
        assert summary.spi.reason == ZERO_PLANNED_VALUE


class TestMetricValueInvariant:
    def test_cannot_construct_a_metric_with_both_value_and_reason(self):
        from src.services.executive_analytics.metrics_engine import MetricValue

        with pytest.raises(ValueError):
            MetricValue(value=Decimal(1), reason="oops")

    def test_cannot_construct_a_metric_with_neither_value_nor_reason(self):
        from src.services.executive_analytics.metrics_engine import MetricValue

        with pytest.raises(ValueError):
            MetricValue(value=None, reason=None)
