"""
tests/scheduler/test_circuit_breaker.py
Unit tests for the retailer source CircuitBreaker.
"""

from datetime import datetime, timedelta, timezone

from scheduler.circuit_breaker import CircuitBreaker


def test_circuit_breaker_healthy_by_default():
    """Breaker is CLOSED and available initially."""
    breaker = CircuitBreaker()
    assert breaker.is_available("amazon") is True
    status = breaker.get_status("amazon")
    assert status["state"] == "CLOSED"


def test_circuit_breaker_trips_on_threshold():
    """Breaker trips to OPEN when failure threshold is reached within window."""
    breaker = CircuitBreaker(failure_threshold=3, window_minutes=10)
    now = datetime.now(timezone.utc)

    # 1st failure
    tripped1 = breaker.record_failure("amazon", "503 Service Unavailable", now=now)
    assert tripped1 is False
    assert breaker.is_available("amazon", now=now) is True

    # 2nd failure
    tripped2 = breaker.record_failure("amazon", "Timeout", now=now)
    assert tripped2 is False

    # 3rd failure (trips)
    tripped3 = breaker.record_failure("amazon", "Captcha blocked", now=now)
    assert tripped3 is True
    assert breaker.is_available("amazon", now=now) is False

    status = breaker.get_status("amazon")
    assert status["state"] == "OPEN"
    assert status["recent_failures"] == 3


def test_circuit_breaker_half_open_and_recovery():
    """Breaker tests recovery after cooldown and resets on success."""
    breaker = CircuitBreaker(failure_threshold=2, cooldown_minutes=15)
    now = datetime(2026, 9, 30, 12, 0, tzinfo=timezone.utc)

    breaker.record_failure("flipkart", "err1", now=now)
    breaker.record_failure("flipkart", "err2", now=now)
    assert breaker.is_available("flipkart", now=now) is False

    # After 16 minutes (cooldown passed) -> enters HALF_OPEN
    later = now + timedelta(minutes=16)
    assert breaker.is_available("flipkart", now=later) is True
    assert breaker.get_status("flipkart")["state"] == "HALF_OPEN"

    # Successful call resets breaker to CLOSED
    breaker.record_success("flipkart")
    assert breaker.get_status("flipkart")["state"] == "CLOSED"
    assert breaker.is_available("flipkart") is True
