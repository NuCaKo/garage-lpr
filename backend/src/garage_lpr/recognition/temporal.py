from collections import Counter
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class TemporalConfirmation:
    plate: str
    confidence: float
    confirmations: int


@dataclass(frozen=True, slots=True)
class _Observation:
    plate: str
    confidence: float
    observed_ns: int


class TemporalPlateValidator:
    """Confirms an exact normalized plate repeatedly within a bounded window."""

    def __init__(
        self,
        min_confidence: float,
        required_confirmations: int,
        confirmation_window_ms: int,
    ) -> None:
        if not 0 <= min_confidence <= 1:
            raise ValueError("Minimum confidence must be within [0, 1]")
        if required_confirmations < 2 or confirmation_window_ms < 1:
            raise ValueError("Temporal validation requires multiple bounded observations")
        self._min_confidence = min_confidence
        self._required_confirmations = required_confirmations
        self._window_ns = confirmation_window_ms * 1_000_000
        self._max_observations = max(32, required_confirmations * 4)
        self._observations: list[_Observation] = []
        self._confirmed = False

    def observe(
        self,
        plate: str,
        confidence: float,
        observed_ns: int,
    ) -> TemporalConfirmation | None:
        if self._confirmed or confidence < self._min_confidence or not plate:
            return None
        cutoff = observed_ns - self._window_ns
        self._observations = [
            observation for observation in self._observations if observation.observed_ns >= cutoff
        ]
        self._observations.append(_Observation(plate, confidence, observed_ns))
        if len(self._observations) > self._max_observations:
            self._observations = self._observations[-self._max_observations :]

        counts = Counter(observation.plate for observation in self._observations)
        eligible = [
            candidate
            for candidate, count in counts.items()
            if count >= self._required_confirmations
        ]
        if not eligible:
            return None
        winner = max(
            eligible,
            key=lambda candidate: (
                counts[candidate],
                sum(item.confidence for item in self._observations if item.plate == candidate),
            ),
        )
        matching = [item for item in self._observations if item.plate == winner]
        self._confirmed = True
        return TemporalConfirmation(
            plate=winner,
            confidence=round(sum(item.confidence for item in matching) / len(matching), 4),
            confirmations=len(matching),
        )
