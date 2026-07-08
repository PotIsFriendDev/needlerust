import random
from typing import List, Tuple

class ContextGenerator:
    def __init__(self, filler_text: str = "The quick brown fox jumps over the lazy dog. "):
        self.filler_text = filler_text

    def generate_needle_context(self, needle: str, total_tokens: int, target_depth: float) -> Tuple[str, int]:
        """
        needle: The fact to hide.
        total_tokens: Approximate target length.
        target_depth: 0.0 (start) to 1.0 (end) of the context.
        """
        # Simple approximation: 1 token ~ 4 chars in English
        estimated_chars = total_tokens * 4
        needle_len = len(needle)
        filler_len = estimated_chars - needle_len

        split_point = int(filler_len * target_depth)

        prefix = (self.filler_text * (split_point // len(self.filler_text) + 1))[:split_point]
        suffix = (self.filler_text * ((filler_len - split_point) // len(self.filler_text) + 1))[:filler_len - split_point]

        return f"{prefix}\n{needle}\n{suffix}", total_tokens

    def generate_noisy_context(self, content: str, noise_level: float) -> str:
        """
        noise_level: percentage of total content that should be noise.
        """
        noise_text = "random unrelated fact: the moon is made of green cheese. " * 10
        noise_len = int(len(content) * (noise_level / (1 - noise_level)))

        # Inject noise at random intervals
        words = content.split()
        noise_words = noise_text.split()

        num_noise_inserts = int(len(words) * noise_level)
        for _ in range(num_noise_inserts):
            pos = random.randint(0, len(words))
            words.insert(pos, random.choice(noise_words))

        return " ".join(words)

class Scenario:
    def __init__(self, name: str, needle: str, total_tokens: int, depth: float, noise: float = 0.0):
        self.name = name
        self.needle = needle
        self.total_tokens = total_tokens
        self.depth = depth
        self.noise = noise

    def __repr__(self):
        return f"Scenario(name={self.name}, depth={self.depth}, tokens={self.total_tokens}, noise={self.noise})"
