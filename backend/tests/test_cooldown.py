from garage_lpr.access.cooldown import CooldownManager, CooldownStatus


def test_cooldown_enforces_plate_and_global_windows() -> None:
    cooldown = CooldownManager(plate_cooldown_seconds=20, global_cooldown_seconds=3)

    assert cooldown.check_and_reserve("34ABC123", 0).status is CooldownStatus.ALLOWED
    same_plate = cooldown.check_and_reserve("34ABC123", 1_000_000_000)
    other_plate = cooldown.check_and_reserve("06XYZ789", 1_000_000_000)
    later = cooldown.check_and_reserve("06XYZ789", 4_000_000_000)

    assert same_plate.status is CooldownStatus.PLATE_COOLDOWN
    assert same_plate.retry_after_seconds == 19
    assert other_plate.status is CooldownStatus.GLOBAL_COOLDOWN
    assert later.status is CooldownStatus.ALLOWED
