from garage_lpr.recognition.temporal import TemporalPlateValidator


def test_temporal_validator_requires_repeated_confident_plate() -> None:
    validator = TemporalPlateValidator(0.85, 3, 2000)

    assert validator.observe("34ABC123", 0.95, 0) is None
    assert validator.observe("34A8C123", 0.92, 300_000_000) is None
    assert validator.observe("34ABC123", 0.96, 600_000_000) is None
    confirmation = validator.observe("34ABC123", 0.94, 900_000_000)

    assert confirmation is not None
    assert confirmation.plate == "34ABC123"
    assert confirmation.confirmations == 3
    assert confirmation.confidence == 0.95
    assert validator.observe("34ABC123", 0.99, 1_000_000_000) is None


def test_temporal_validator_drops_old_and_low_confidence_observations() -> None:
    validator = TemporalPlateValidator(0.85, 2, 500)

    assert validator.observe("34ABC123", 0.99, 0) is None
    assert validator.observe("34ABC123", 0.40, 100_000_000) is None
    assert validator.observe("34ABC123", 0.99, 700_000_000) is None
    assert validator.observe("34ABC123", 0.99, 900_000_000) is not None
