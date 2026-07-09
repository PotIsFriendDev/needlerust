import os
from openai import OpenAI
from typing import List, Dict, Any, Optional

class LLMClient:
    def __init__(self, api_key: str, base_url: str, model: str):
        self.client = OpenAI(api_key=api_key, base_url=base_url)
        self.model = model

    def get_completion(
        self,
        prompt: str,
        system_prompt: str = "You are a helpful assistant.",
        max_tokens: Optional[int] = None,
        pressure_instruction: Optional[str] = None,
    ) -> str:
        try:
            # Output-length pressure: when a non-zero pressure is requested we
            # force a high max_tokens and prepend a directive that asks the
            # model to keep generating until the budget is consumed. This
            # exposes the autoregressive drift that long outputs induce on
            # earlier-context recall.
            if pressure_instruction and pressure_instruction.strip():
                prompt = f"{prompt}\n\n{pressure_instruction}"

            kwargs: Dict[str, Any] = {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt},
                ],
                "temperature": 0,
            }
            if max_tokens is not None and max_tokens > 0:
                kwargs["max_tokens"] = max_tokens
            response = self.client.chat.completions.create(**kwargs)
            return response.choices[0].message.content or ""
        except Exception as e:
            print(f"Error during API call: {e}")
            return ""

    def get_token_count(self, text: str) -> int:
        """
        Approximate token count using 1 token ~ 4 chars.
        Can be overridden with a real tokenizer (e.g. tiktoken).
        """
        return len(text) // 4


    def get_completion_batch(self, prompts: List[str], system_prompt: str = "You are a helpful assistant.") -> List[str]:
        return [self.get_completion(p, system_prompt) for p in prompts]
