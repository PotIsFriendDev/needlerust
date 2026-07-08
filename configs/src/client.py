import os
from openai import OpenAI
from typing import List, Dict, Any

class LLMClient:
    def __init__(self, api_key: str, base_url: str, model: str):
        self.client = OpenAI(api_key=api_key, base_url=base_url)
        self.model = model

    def get_completion(self, prompt: str, system_prompt: str = "You are a helpful assistant.") -> str:
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt}
                ],
                temperature=0, # Low temperature for reproducible evaluation
            )
            return response.choices[0].message.content
        except Exception as e:
            print(f"Error during API call: {e}")
            return ""

    def get_completion_batch(self, prompts: List[str], system_prompt: str = "You are a helpful assistant.") -> List[str]:
        return [self.get_completion(p, system_prompt) for p in prompts]
