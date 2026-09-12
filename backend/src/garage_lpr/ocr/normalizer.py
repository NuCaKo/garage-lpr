import re
from dataclasses import dataclass

SEPARATORS = re.compile(r"[\s.\-]+")
ALPHANUMERIC = re.compile(r"^[A-Z0-9]+$")
TURKISH_PLATE = re.compile(r"^(0[1-9]|[1-7][0-9]|8[01])[A-Z]{1,3}[0-9]{2,4}$")
TO_DIGIT = {"O": "0", "I": "1", "S": "5", "B": "8"}
TO_LETTER = {value: key for key, value in TO_DIGIT.items()}


@dataclass(frozen=True, slots=True)
class NormalizedPlate:
    text: str
    valid_format: bool
    corrections: tuple[str, ...] = ()


class TurkishPlateNormalizer:
    """Normalizes formatting and corrects ambiguous glyphs only by plate position."""

    def normalize(self, raw_text: str) -> NormalizedPlate:
        canonical = SEPARATORS.sub("", raw_text).upper()
        if not canonical or not ALPHANUMERIC.fullmatch(canonical):
            return NormalizedPlate(canonical, False)
        if TURKISH_PLATE.fullmatch(canonical):
            return NormalizedPlate(canonical, True)

        candidates: dict[str, tuple[str, ...]] = {}
        for letter_count in range(1, 4):
            digit_count = len(canonical) - 2 - letter_count
            if not 2 <= digit_count <= 4:
                continue
            transformed, corrections = self._transform(canonical, letter_count)
            if TURKISH_PLATE.fullmatch(transformed):
                candidates[transformed] = corrections

        if not candidates:
            return NormalizedPlate(canonical, False)
        fewest = min(len(value) for value in candidates.values())
        winners = [text for text, changes in candidates.items() if len(changes) == fewest]
        if len(winners) != 1:
            return NormalizedPlate(canonical, False)
        winner = winners[0]
        return NormalizedPlate(winner, True, candidates[winner])

    @staticmethod
    def _transform(text: str, letter_count: int) -> tuple[str, tuple[str, ...]]:
        output: list[str] = []
        corrections: list[str] = []
        letter_end = 2 + letter_count
        for index, character in enumerate(text):
            mapping = TO_LETTER if 2 <= index < letter_end else TO_DIGIT
            replacement = mapping.get(character, character)
            output.append(replacement)
            if replacement != character:
                corrections.append(f"{index}:{character}>{replacement}")
        return "".join(output), tuple(corrections)
