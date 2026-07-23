import logging

from src.services.events.noop_emitter import NoOpEventEmitter


def test_emit_logs_and_returns_none(caplog):
    emitter = NoOpEventEmitter()

    with caplog.at_level(logging.INFO, logger="src.services.events.noop_emitter"):
        result = emitter.emit("portfolio.created", {"portfolio_id": 1}, 7)

    assert result is None
    message = caplog.records[-1].getMessage()
    assert "portfolio.created" in message
    assert "org=7" in message
