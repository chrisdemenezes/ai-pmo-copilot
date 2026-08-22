from datetime import date
from decimal import Decimal

from src.services.executive_analytics.executive_signal_engine import (
    COST_PERFORMANCE_DETERIORATING,
    FORECAST_DEVIATION,
    RECOVERY_TREND,
    SCHEDULE_PERFORMANCE_DETERIORATING,
    SEVERITY_CRITICAL,
    SEVERITY_WARNING,
    derive_cost_performance_signal,
    derive_forecast_deviation_signal,
    derive_schedule_performance_signal,
)
from src.services.executive_analytics.metrics_engine import (
    EvmSummary,
    HistoryPoint,
    MetricValue,
)


def _point(as_of: date, ev, ac, pv) -> HistoryPoint:
    return HistoryPoint(
        as_of=as_of,
        ev=MetricValue.present(Decimal(ev)) if ev is not None else MetricValue.na("no_snapshot_captured"),
        ac=MetricValue.present(Decimal(ac)) if ac is not None else MetricValue.na("no_snapshot_captured"),
        pv=MetricValue.present(Decimal(pv)) if pv is not None else MetricValue.na("no_baseline_defined"),
    )


class TestDeriveCostPerformanceSignal:
    def test_returns_none_with_fewer_than_2_usable_points(self):
        history = [_point(date(2026, 1, 1), 100, 100, 100)]
        assert derive_cost_performance_signal(history, "Projeto A") is None

    def test_flags_deteriorating_when_cpi_falls(self):
        history = [_point(date(2026, 1, 1), 100, 100, 100), _point(date(2026, 2, 1), 80, 100, 100)]

        signal = derive_cost_performance_signal(history, "Projeto A")

        assert signal.signal_type == COST_PERFORMANCE_DETERIORATING
        assert signal.trend == "down"
        assert signal.severity == SEVERITY_CRITICAL

    def test_flags_recovery_trend_when_cpi_improves(self):
        history = [_point(date(2026, 1, 1), 80, 100, 100), _point(date(2026, 2, 1), 100, 100, 100)]

        signal = derive_cost_performance_signal(history, "Projeto A")

        assert signal.signal_type == RECOVERY_TREND
        assert signal.trend == "up"

    def test_returns_none_when_cpi_does_not_change(self):
        history = [_point(date(2026, 1, 1), 100, 100, 100), _point(date(2026, 2, 1), 100, 100, 100)]
        assert derive_cost_performance_signal(history, "Projeto A") is None

    def test_skips_points_where_ac_is_missing_rather_than_treating_it_as_zero(self):
        history = [
            _point(date(2026, 1, 1), 100, None, 100),
            _point(date(2026, 2, 1), 90, 100, 100),
            _point(date(2026, 3, 1), 80, 100, 100),
        ]

        signal = derive_cost_performance_signal(history, "Projeto A")

        assert "2026-02-01" in signal.evidence_reference
        assert "2026-03-01" in signal.evidence_reference


class TestDeriveSchedulePerformanceSignal:
    def test_flags_deteriorating_when_spi_falls(self):
        history = [_point(date(2026, 1, 1), 100, 100, 100), _point(date(2026, 2, 1), 70, 100, 100)]

        signal = derive_schedule_performance_signal(history, "Projeto A")

        assert signal.signal_type == SCHEDULE_PERFORMANCE_DETERIORATING


class TestDeriveForecastDeviationSignal:
    def _summary(self, bac, vac) -> EvmSummary:
        na = MetricValue.na("no_baseline_defined")
        return EvmSummary(
            bac=MetricValue.present(Decimal(bac)) if bac is not None else na,
            pv=na,
            ev=na,
            ac=na,
            cpi=na,
            spi=na,
            cv=na,
            sv=na,
            eac=na,
            etc=na,
            vac=MetricValue.present(Decimal(vac)) if vac is not None else na,
        )

    def test_returns_none_when_bac_or_vac_is_not_available(self):
        assert derive_forecast_deviation_signal(self._summary(None, -5000), "Projeto A", date(2026, 2, 1)) is None
        assert derive_forecast_deviation_signal(self._summary(100000, None), "Projeto A", date(2026, 2, 1)) is None

    def test_returns_none_when_deviation_is_below_threshold(self):
        summary = self._summary(100000, -5000)
        assert derive_forecast_deviation_signal(summary, "Projeto A", date(2026, 2, 1)) is None

    def test_flags_forecast_deviation_when_ratio_exceeds_threshold(self):
        summary = self._summary(100000, -15000)

        signal = derive_forecast_deviation_signal(summary, "Projeto A", date(2026, 2, 1))

        assert signal.signal_type == FORECAST_DEVIATION
        assert signal.trend == "down"
        assert signal.severity == SEVERITY_WARNING

    def test_is_critical_when_deviation_is_severe(self):
        summary = self._summary(100000, -30000)

        signal = derive_forecast_deviation_signal(summary, "Projeto A", date(2026, 2, 1))

        assert signal.severity == SEVERITY_CRITICAL
