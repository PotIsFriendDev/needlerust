import os
import traceback
from openai import OpenAI
from typing import List, Dict, Any, Optional, Tuple


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
    ) -> Tuple[str, str]:
        """
        Returns (content, error).

        - content: the model's text, or "" if no content was produced.
        - error: "" on success; otherwise a short human-readable
          description of the failure (exception class + first line of
          the message). Callers must surface this to the result row
          so infrastructure failures are distinguishable from
          "model answered wrong".
        """
        try:
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
            content = response.choices[0].message.content or ""
            return content, ""
        except Exception as e:
            msg = f"{type(e).__name__}: {str(e).splitlines()[0] if str(e) else 'no message'}"
            print(f"Error during API call: {msg}")
            traceback.print_exc()
            return "", msg

    def get_token_count(self, text: str) -> int:
        """
        Approximate token count using 1 token ~ 4 chars.
        Can be overridden with a real tokenizer (e.g. tiktoken).
        """
        return len(text) // 4


    def get_completion_batch(self, prompts: List[str], system_prompt: str = "You are a helpful assistant.") -> List[Tuple[str, str]]:
        return [self.get_completion(p, system_prompt) for p in prompts]

