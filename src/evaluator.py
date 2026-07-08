from typing import List, Tuple, Dict, Any
import numpy as np

class Evaluator:
    def __init__(self, method: str = "exact"):
        self.method = method

    def check_accuracy(self, needle: str, response: str) -> float:
        """
        Returns a score from 0.0 to 1.0.
        Methods:
        - 'exact': 1.0 if needle in response, else 0.0
        - 'semantic': Placeholder for semantic similarity
        """
        if not response:
            return 0.0

        if self.method == "exact":
            return 1.0 if needle.lower() in response.lower() else 0.0

        elif self.method == "semantic":
            # Simplified semantic check: token overlap ratio
            needle_tokens = set(needle.lower().split())
            response_tokens = set(response.lower().split())
            if not needle_tokens: return 0.0
            intersection = needle_tokens.intersection(response_tokens)
            return len(intersection) / len(needle_tokens)

        return 0.0

    def calculate_conflict_resolution(self, needles: List[str], response: str) -> float:
        """
        Measures how well the model resolves conflicting information.
        Expects a list of needles where some are conflicting.
        """
        scores = [self.check_accuracy(n, response) for n in needles]
        return sum(scores) / len(needles) if needles else 0.0

    def calculate_rot(self, success_rates: List[float]) -> float:
        """
        Calculates the decay rate. Simple version: drop from start to end.
        """
        if len(success_rates) < 2:
            return 0.0

        start_perf = success_rates[0]
        end_perf = success_rates[-1]

        return start_perf - end_perf
