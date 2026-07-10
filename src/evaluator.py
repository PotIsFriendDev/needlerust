import re
from typing import List, Tuple, Dict, Any
import numpy as np


def normalize_response(response: str) -> str:
    """
    Strips the noise that reasoner / markdown outputs wrap around the actual
    answer so the needle can be matched as a substring. Order matters.
    """
    if not response:
        return ""

    s = response

    # 1. Cut off everything before the first explicit "Final Answer:" marker.
    #    Reasoner models (deepseek-reasoner, o1) often emit their reasoning
    #    before the answer; we only want the post-reasoning tail.
    final_match = re.search(r"(?im)^\s*final\s*answer\s*[:：]?\s*", s)
    if final_match:
        s = s[final_match.end():]

    # 2. LaTeX boxed answers: \boxed{12345} -> 12345
    s = re.sub(r"\\boxed\{([^{}]+)\}", r"\1", s)

    # 3. Markdown emphasis: **12345**, *12345*, __12345__, _12345_
    s = re.sub(r"\*\*(.+?)\*\*", r"\1", s)
    s = re.sub(r"__(.+?)__", r"\1", s)
    s = re.sub(r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)", r"\1", s)
    s = re.sub(r"(?<!_)_(?!_)(.+?)(?<!_)_(?!_)", r"\1", s)

    # 4. Inline code: `12345` -> 12345
    s = re.sub(r"`([^`]+)`", r"\1", s)

    # 5. Normalize curly quotes / dashes
    s = s.replace(""", "'").replace(""", "'")
    s = s.replace("—", "-").replace("–", "-")

    # 6. Strip thousands-separators in digit runs: "12,345" -> "12345"
    s = re.sub(r"(\d),(\d)", r"\1\2", s)

    # 7. Collapse all whitespace (incl. newlines) to a single space
    s = re.sub(r"\s+", " ", s).strip()

    return s


def _extract_digit_substrings(s: str) -> List[str]:
    """
    For needle patterns that are mostly digits (codes, IDs), pull out every
    contiguous digit run and return them as length-5+ candidates. Lets us
    match "the code is 12345" against needle "12345" even when the model
    adds surrounding text or punctuation.
    """
    return [m.group(0) for m in re.finditer(r"\d{3,}", s)]


def _extract_identifiers(s: str) -> List[str]:
    """
    Pull out "key-like" identifiers from the needle: runs of uppercase
    letters and digits connected by hyphens (e.g. BLUE-OCEAN-7421,
    NIGHTHAWK, HARRIER-19). Catches the case where the model returns
    just the bare ID and we still want to score 1.0 against a long
    multi-fact needle. Skips runs shorter than 3 chars to avoid matching
    ordinary English words.
    """
    return [m.group(0) for m in re.finditer(r"\b[A-Z0-9]+(?:-[A-Z0-9]+)*\b", s) if len(m.group(0)) >= 3]


def _needle_key_facts(needle: str) -> List[str]:
    """
    Split a long needle into the per-sentence facts it asserts. A response
    matches if it contains ANY of these sentences (after normalization).
    For short single-fact needles (no internal sentence breaks), returns
    the needle as the single fact.
    """
    parts = re.split(r"(?<=[.!?])\s+", needle.strip())
    parts = [p for p in parts if p]
    return parts if len(parts) > 1 else [needle]


class Evaluator:
    def __init__(self, method: str = "exact"):
        self.method = method

    def check_accuracy(self, needle: str, response: str) -> float:
        """
        Returns a score from 0.0 to 1.0.
        Methods:
        - 'exact': 1.0 if ANY key fact from the needle appears in the
          normalized response. A "key fact" is one sentence of the needle,
          which makes this work for both short single-fact needles
          ("code is 12345") and long multi-fact needles.
        - 'semantic': fraction of needle sentences that appear in the
          response.
        """
        if not response:
            return 0.0

        normalized = normalize_response(response)
        if not normalized:
            return 0.0

        needle_lower = needle.lower()
        normalized_lower = normalized.lower()
        facts = _needle_key_facts(needle)
        facts_lower = [f.lower() for f in facts]

        if self.method == "exact":
            # 0. Identifier fallback (case-insensitive): if the needle
            #    contains any key-like ID (BLUE-OCEAN-7421, NIGHTHAWK,
            #    HARRIER-19, ...) and that ID appears in the response,
            #    score 1.0. Runs BEFORE the substring / fact / prefix
            #    checks so that a bare-ID response against a long
            #    multi-fact needle still scores correctly. Step 4's
            #    digit-only fallback is now only needed for IDs that
            #    happen to be pure digits.
            for ident in _extract_identifiers(needle):
                if ident.lower() in normalized_lower:
                    return 1.0

            # 1. Whole-needle substring (handles short single-fact needles)
            if needle_lower in normalized_lower:
                return 1.0

            # 2. Any per-sentence key fact from the needle appears as a
            #    substring in the response (model quoted a full sentence).
            for fact in facts_lower:
                if fact and fact in normalized_lower:
                    return 1.0

            # 3. Prefix match (model paraphrased a fragment of a fact):
            #    "The deputy director signs off on all access changes."
            #    in the needle should match a response of
            #    "The deputy director signs off.".
            for fact in facts_lower:
                if not fact or len(fact) < 20:
                    continue
                if normalized_lower.startswith(fact[:20]):
                    return 1.0
                if len(normalized_lower) >= 10 and fact.startswith(normalized_lower[:20]):
                    return 1.0

            # 4. Digit-substring fallback: needle is a code like "12345"
            needle_digits = re.sub(r"\D", "", needle_lower)
            if len(needle_digits) >= 3:
                response_digits = "".join(_extract_digit_substrings(normalized))
                if needle_digits in response_digits:
                    return 1.0

            return 0.0

        elif self.method == "semantic":
            matched = sum(1 for f in facts_lower if f and f in normalized_lower)
            return matched / len(facts_lower) if facts_lower else 0.0

        return 0.0

    def calculate_conflict_resolution(self, needles: List[str], response: str) -> float:
        scores = [self.check_accuracy(n, response) for n in needles]
        return sum(scores) / len(needles) if needles else 0.0

    def calculate_rot(self, success_rates: List[float]) -> float:
        if len(success_rates) < 2:
            return 0.0
        return success_rates[0] - success_rates[-1]
