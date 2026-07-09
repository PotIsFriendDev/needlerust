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


class StructureAssembler(AssemblerStep):
    def __init__(self, filler_text: str = "The quick brown fox jumps over the lazy dog. "):
        self.filler_text = filler_text

    def assemble(self, content: str, params: Dict[str, Any]) -> str:
        needles = [content]
        additional_needles = params.get('additional_needles', [])
        if isinstance(additional_needles, list):
            needles.extend(additional_needles)

        total_tokens = params.get('total_tokens', 2048)
        strategy = params.get('placement_strategy', 'interleaved')

        estimated_chars = total_tokens * 4

        total_needle_len = sum(len(n) for n in needles)
        filler_len = estimated_chars - total_needle_len

        if strategy == 'cluster':
            target_depth = params.get('depth', 0.5)
            split_point = int(filler_len * target_depth)

            prefix = (self.filler_text * (split_point // len(self.filler_text) + 1))[:split_point]
            suffix = (self.filler_text * ((filler_len - split_point) // len(self.filler_text) + 1))[:filler_len - split_point]

            needle_block = "\n".join(needles)
            return f"{prefix}\n{needle_block}\n{suffix}"

        points = []
        for i, n in enumerate(needles):
            if hasattr(n, 'depth'):
                points.append((n.depth, n.content))
            else:
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

        final_filler_len = estimated_chars - len(result)
        if final_filler_len > 0:
            result += (self.filler_text * (final_filler_len // len(self.filler_text) + 1))[:final_filler_len]

        return result


class DistanceAssembler(AssemblerStep):
    """
    Models the absolute token distance from the instruction (system prompt)
    to the context, and from the context to the query.

    Factor: instruction_distance (int, tokens)
        - Inserts `instruction_distance` tokens of padding BEFORE the context,
          simulating a long chain of system-level / developer instructions
          stacked above the retrieved context.

    Factor: query_distance (int, tokens)
        - Inserts `query_distance` tokens of padding AFTER the context and
          BEFORE the question is asked, simulating follow-up turns or
          extra retrieved material between the needle and the query.
    """

    FILLER = "The grass is green. The sky is blue. The sun is bright. "

    def assemble(self, content: str, params: Dict[str, Any]) -> str:
        instruction_distance = int(params.get('instruction_distance', 0))
        query_distance = int(params.get('query_distance', 0))

        if instruction_distance <= 0 and query_distance <= 0:
            return content

        prefix = self._padding(instruction_distance) if instruction_distance > 0 else ""
        suffix = self._padding(query_distance) if query_distance > 0 else ""

        return f"{prefix}{content}{suffix}"

    @staticmethod
    def _padding(tokens: int) -> str:
        chars = max(tokens, 0) * 4
        if chars <= 0:
            return ""
        block = DistanceAssembler.FILLER
        return (block * (chars // len(block) + 1))[:chars]


class FragmentationAssembler(AssemblerStep):
    """
    Simulates KV-cache fragmentation by splitting the context into N
    non-contiguous chunks separated by gaps. The needle is hidden in one
    of the chunks; the others are pure filler.

    Factors:
        - fragment_count (int): number of chunks in the assembled context.
        - needle_fragment_index (int): which chunk (0-based) holds the needle.
        - gap_tokens (int): token count of the "gap" between each pair of
          consecutive chunks (modeled as ellipsis + filler to mimic the
          prefill discontinuity of long contexts).
    """

    FILLER = "Lorem ipsum dolor sit amet, consectetur adipiscing elit. "
    GAP = "\n[...elided {} tokens...]\n"

    def assemble(self, content: str, params: Dict[str, Any]) -> str:
        fragment_count = int(params.get('fragment_count', 1))
        if fragment_count <= 1:
            return content

        needle_fragment_index = int(params.get('needle_fragment_index', 0))
        needle_fragment_index = max(0, min(needle_fragment_index, fragment_count - 1))

        gap_tokens = int(params.get('gap_tokens', 0))
        total_tokens = int(params.get('total_tokens', 2048))
        estimated_chars = total_tokens * 4

        # Subtract the needle's own size and the gap overhead from the
        # budget so the final length stays close to total_tokens.
        gap_chars = gap_tokens * 4
        needle_len = len(content)
        budget = max(estimated_chars - needle_len - gap_chars * (fragment_count - 1), 0)
        chunk_chars = max(budget // fragment_count, 1)

        chunks = []
        for i in range(fragment_count):
            chunk = (self.FILLER * (chunk_chars // len(self.FILLER) + 1))[:chunk_chars]
            chunks.append(chunk)

        # Splice the needle into the target chunk.
        target = chunks[needle_fragment_index]
        mid = len(target) // 2
        chunks[needle_fragment_index] = target[:mid] + f"\n{content}\n" + target[mid:]

        gap = self.GAP.format(gap_tokens) if gap_tokens > 0 else "\n\n"
        return gap.join(chunks)


class SemanticAssembler(AssemblerStep):
    def assemble(self, content: str, params: Dict[str, Any]) -> str:
        distractors = params.get('semantic_distractors', [])
        if not distractors:
            return content

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
    def __init__(self, include_distance: bool = True, include_fragmentation: bool = True):
        self.pipeline: List[AssemblerStep] = [
            StructureAssembler(),
            SemanticAssembler(),
            InterferenceAssembler(),
            BoundaryAssembler(),
        ]
        # The two newer steps mutate the entire buffer (length-budgeted) so
        # they have to run before the length-bounded steps; we splice them
        # at the head of the pipeline.
        if include_distance:
            self.pipeline.insert(0, DistanceAssembler())
        if include_fragmentation:
            self.pipeline.insert(1, FragmentationAssembler())

    def assemble(self, needle: str, params: Dict[str, Any]) -> str:
        content = needle
        for step in self.pipeline:
            content = step.assemble(content, params)
        return content


# ---- Task complexity ladder -------------------------------------------------
# Three difficulty rungs. The "task_complexity" factor selects between these
# templates; using a longer chain forces the model to perform multi-hop or
# deductive reasoning over the context rather than a single string match.

TASK_TEMPLATES: Dict[str, str] = {
    "simple": (
        "Context:\n{context}\n\n"
        "Question: {question}\n"
        "Answer concisely with the exact fact from the context."
    ),
    "multi_hop": (
        "Context:\n{context}\n\n"
        "You will be asked a question that requires combining TWO distinct "
        "pieces of information found in the context above. Identify both "
        "pieces explicitly before answering.\n\n"
        "Question: {question}\n"
        "Reasoning: <list the two pieces you combined>\n"
        "Final answer:"
    ),
    "complex": (
        "Context:\n{context}\n\n"
        "Reasoning task: First, identify ALL facts in the context that are "
        "relevant to the question. Second, discard any that contradict each "
        "other. Third, perform the logical/arithmetic step required to derive "
        "the final answer.\n\n"
        "Question: {question}\n"
        "Step 1 (relevant facts):\n"
        "Step 2 (contradiction check):\n"
        "Step 3 (derivation):\n"
        "Final answer:"
    ),
}


def resolve_task_template(task_complexity: str, fallback: str) -> str:
    return TASK_TEMPLATES.get(task_complexity, fallback)
