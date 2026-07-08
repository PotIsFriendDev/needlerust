from typing import List, Tuple

class Evaluator:
    @staticmethod
    def check_accuracy(needle: str, response: str) -> float:
        """
        Returns 1.0 if needle is in response, 0.0 otherwise.
        Can be expanded to use semantic similarity.
        """
        if not response:
            return 0.0

        # Simple contain check for the 'needle'
        if needle.lower() in response.lower():
            return 1.0

        return 0.0

    @staticmethod
    def calculate_rot(success_rates: List[float]) -> float:
        """
        Calculates the decay rate. Simple version: drop from start to end.
        """
        if len(success_rates) < 2:
            return 0.0

        start_perf = success_rates[0]
        end_perf = success_rates[-1]

        return start_perf - end_perf
