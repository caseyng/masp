import html
import re
from dataclasses import dataclass


@dataclass
class BoundaryResult:
    safe: bool
    failure_mode: str | None = None

    def __repr__(self) -> str:
        if self.safe:
            return "BoundaryResult(safe=True)"
        return f"BoundaryResult(safe=False, failure_mode={self.failure_mode!r})"


class LLMBoundary:
    _INJECTION_PATTERNS = [
        r"\[INST\]",
        r"<s>",
        r"###\s*[Ss]ystem",
        r"###\s*[Ii]nstruction",
        r"ignore\s+previous",
        r"disregard.*instructions",
        r"you\s+are\s+now\s+(?:a|an|the)\s+\w",
        r"override\s+.*instructions",
        r"new\s+instructions\s*:",
    ]
    _OUTPUT_PATTERNS = [
        r"jailbreak",
        r"DAN\s+mode",
        r"system\s+prompt\s*:",
        r"i\s+am\s+now\s+free",
    ]

    def check_input(self, text: str) -> BoundaryResult:
        if not text:
            raise ValueError("text must be non-empty")
        normalised = self._normalise(text)
        if self._matches(normalised, self._INJECTION_PATTERNS):
            return BoundaryResult(safe=False, failure_mode="boundary_injection_detected")
        return BoundaryResult(safe=True)

    def check_output(self, text: str) -> BoundaryResult:
        if not text:
            raise ValueError("text must be non-empty")
        if self._matches(text, self._OUTPUT_PATTERNS):
            return BoundaryResult(safe=False, failure_mode="boundary_output_unsafe")
        return BoundaryResult(safe=True)

    def _normalise(self, text: str) -> str:
        result = html.unescape(text)
        result = re.sub(
            r"\\u([0-9a-fA-F]{4})",
            lambda m: chr(int(m.group(1), 16)),
            result,
        )
        return result

    def _matches(self, text: str, patterns: list[str]) -> bool:
        return any(re.search(p, text, re.IGNORECASE) for p in patterns)

    def __repr__(self) -> str:
        return "LLMBoundary()"
