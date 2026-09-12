import pytest

from garage_lpr.ocr.normalizer import TurkishPlateNormalizer


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("34 ABC 123", "34ABC123"),
        ("34-ABC-123", "34ABC123"),
        ("34abc123", "34ABC123"),
        ("34.ABC.123", "34ABC123"),
    ],
)
def test_normalizer_removes_formatting_without_glyph_changes(raw: str, expected: str) -> None:
    result = TurkishPlateNormalizer().normalize(raw)

    assert result.text == expected
    assert result.valid_format is True
    assert result.corrections == ()


def test_normalizer_corrects_ambiguous_glyph_only_in_letter_context() -> None:
    result = TurkishPlateNormalizer().normalize("34A8C123")

    assert result.text == "34ABC123"
    assert result.valid_format is True
    assert result.corrections == ("3:8>B",)


def test_normalizer_corrects_province_and_suffix_in_numeric_context() -> None:
    result = TurkishPlateNormalizer().normalize("O1ABC12B")

    assert result.text == "01ABC128"
    assert result.valid_format is True
    assert result.corrections == ("0:O>0", "7:B>8")


@pytest.mark.parametrize("raw", ["00ABC123", "82ABC123", "34AB#123", "not-a-plate"])
def test_normalizer_rejects_invalid_or_ambiguous_formats(raw: str) -> None:
    assert TurkishPlateNormalizer().normalize(raw).valid_format is False
