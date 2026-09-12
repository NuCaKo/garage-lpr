import json
from pathlib import Path

from garage_lpr.resilience.domain import StabilityReport


class AtomicReportWriter:
    """Replaces one small JSON report so long tests cannot grow disk without bound."""

    def __init__(self, output_path: Path) -> None:
        self._output_path = output_path

    def write(self, report: StabilityReport) -> None:
        self._output_path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self._output_path.with_suffix(f"{self._output_path.suffix}.tmp")
        temporary.write_text(
            json.dumps(report.as_dict(), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        temporary.replace(self._output_path)
