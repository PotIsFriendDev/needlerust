import random
from typing import List, Tuple, Dict, Any, Optional, Union
from dataclasses import dataclass
from abc import ABC, abstractmethod

@dataclass
class Needle:
    content: str
    depth: float
    id: str = "main"

class AssemblerStep(ABC):
    @abstractmethod
    def assemble(self, content: str, params: Dict[str, Any]) -> str:
        pass


class AssemblerStep(ABC):
    @abstractmethod
    def assemble(self, content: str, params: Dict[str, Any]) -> str:
        pass

class StructureAssembler(AssemblerStep):
    def __init__(self, filler_text: str = "The quick brown fox jumps over the lazy dog. "):
        self.filler_text = filler_text

    def assemble(self, content: str, params: Dict[str, Any]) -> str:
        # 'content' is the primary needle.
        # We support multiple needles via params['additional_needles'].
        needles = [content]
        additional_needles = params.get('additional_needles', [])
        if isinstance(additional_needles, list):
            needles.extend(additional_needles)

        total_tokens = params.get('total_tokens', 2048)
        strategy = params.get('placement_strategy', 'interleaved') # 'cluster' or 'interleaved'

        # Simple approximation: 1 token ~ 4 chars
        estimated_chars = total_tokens * 4

        # Calculate total needle length
        total_needle_len = sum(len(n) for n in needles)
        filler_len = estimated_chars - total_needle_len

        if strategy == 'cluster':
            # Place all needles together around the target depth
            target_depth = params.get('depth', 0.5)
            split_point = int(filler_len * target_depth)

            prefix = (self.filler_text * (split_point // len(self.filler_text) + 1))[:split_point]
            suffix = (self.filler_text * ((filler_len - split_point) // len(self.filler_text) + 1))[:filler_len - split_point]

            needle_block = "\n".join(needles)
            return f"{prefix}\n{needle_block}\n{suffix}"

        else: # interleaved
            # Spread needles across the context
            # For simplicity, we'll distribute them evenly if no specific depths are given
            # or use their specified depths if they are objects.

            # Let's assume needles can be strings or Needle objects
            # If strings, we'll distribute them.

            points = []
            for i, n in enumerate(needles):
                if hasattr(n, 'depth'):
                    points.append((n.depth, n.content))
                else:
                    # distribute evenly
                    depth = (i + 0.5) / len(needles)
                    points.append((depth, n))

            points.sort()

            result = ""
            last_pos = 0
            for depth, text in points:
                current_pos = int(estimated_chars * depth)
                segment_len = current_pos - last_pos - len(text)
                if segment_len > 0:
                    segment = (self.filler_text * (segment_len // len(self.filler_text) + 1))[:segment_len]
                    result += segment
                result += f"\n{text}\n"
                last_pos = current_pos + len(text)

            # Add final filler
            final_filler_len = estimated_chars - len(result)
            if final_filler_len > 0:
                result += (self.filler_text * (final_filler_len // len(self.filler_text) + 1))[:final_filler_len]

            return result

class SemanticAssembler(AssemblerStep):
    def assemble(self, content: str, params: Dict[str, Any]) -> str:
        distractors = params.get('semantic_distractors', [])
        if not distractors:
            return content

        # Simple implementation: insert distractors at random positions
        words = content.split()
        for d in distractors:
            pos = random.randint(0, len(words))
            words.insert(pos, d)
        return " ".join(words)

class InterferenceAssembler(AssemblerStep):
    def assemble(self, content: str, params: Dict[str, Any]) -> str:
        noise_level = params.get('noise', 0.0)
        if noise_level <= 0:
            return content

        noise_text = "random unrelated fact: the moon is made of green cheese. "
        words = content.split()
        num_noise_inserts = int(len(words) * noise_level)

        for _ in range(num_noise_inserts):
            pos = random.randint(0, len(words))
            words.insert(pos, random.choice(noise_text.split()))
        return " ".join(words)

class BoundaryAssembler(AssemblerStep):
    def assemble(self, content: str, params: Dict[str, Any]) -> str:
        format_type = params.get('format', 'plaintext')
        if format_type == 'markdown':
            return f"# Document\n\n{content}\n\n---\nEnd of document"
        elif format_type == 'xml':
            return f"<doc>\n<content>\n{content}\n</content>\n</doc>"
        elif format_type == 'json':
            import json
            return json.dumps({"document": content}, indent=2)
        return content

class ContextAssembler:
    def __init__(self):
        self.pipeline: List[AssemblerStep] = [
            StructureAssembler(),
            SemanticAssembler(),
            InterferenceAssembler(),
            BoundaryAssembler()
        ]

    def assemble(self, needle: str, params: Dict[str, Any]) -> str:
        content = needle
        for step in self.pipeline:
            content = step.assemble(content, params)
        return content
