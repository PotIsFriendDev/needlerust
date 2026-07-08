import pandas as pd
import os
import json
import hashlib
from datetime import datetime
from typing import List, Dict, Any
from .client import LLMClient
from .generators import ContextGenerator, Scenario
from .evaluator import Evaluator
from tqdm import tqdm

class RustSimulator:
    def __init__(self, client: LLMClient, results_dir: str = "results", cache_file: str = "cache.json"):
        self.client = client
        self.results_dir = results_dir
        self.cache_file = os.path.join(results_dir, cache_file)
        self.generator = ContextGenerator()
        self.evaluator = Evaluator()

        if not os.path.exists(results_dir):
            os.makedirs(results_dir)

        self.cache = self._load_cache()

    def _load_cache(self) -> Dict[str, Any]:
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"Warning: Could not load cache: {e}")
        return {}

    def _save_cache(self):
        with open(self.cache_file, 'w', encoding='utf-8') as f:
            json.dump(self.cache, f, ensure_ascii=False, indent=2)

    def _generate_scenario_hash(self, scenario: Scenario, question: str) -> str:
        # Create a unique hash based on all factors that affect the output
        input_str = f"{scenario.name}|{scenario.needle}|{scenario.total_tokens}|{scenario.depth}|{scenario.noise}|{question}"
        return hashlib.sha256(input_str.encode()).hexdigest()

    def run_experiment(self, scenarios: List[Scenario], question: str, use_cache: bool = True, force_refresh: bool = False):
        results = []
        saved_tokens_count = 0

        for scenario in tqdm(scenarios, desc="Running scenarios"):
            scenario_hash = self._generate_scenario_hash(scenario, question)

            # 1. Check Cache
            if use_cache and not force_refresh and scenario_hash in self.cache:
                cached_res = self.cache[scenario_hash]
                results.append(cached_res)
                saved_tokens_count += 1
                continue

            # 2. Generate Context
            context, _ = self.generator.generate_needle_context(
                scenario.needle, scenario.total_tokens, scenario.depth
            )

            if scenario.noise > 0:
                context = self.generator.generate_noisy_context(context, scenario.noise)

            # 3. Query LLM
            prompt = f"Context:\n{context}\n\nQuestion: {question}\nAnswer:"
            response = self.client.get_completion(prompt)

            # 4. Evaluate
            accuracy = self.evaluator.check_accuracy(scenario.needle, response)

            res_data = {
                "scenario": scenario.name,
                "depth": scenario.depth,
                "tokens": scenario.total_tokens,
                "noise": scenario.noise,
                "accuracy": accuracy,
                "response": response
            }

            results.append(res_data)

            # Update cache
            if use_cache:
                self.cache[scenario_hash] = res_data

        if use_cache:
            self._save_cache()

        if saved_tokens_count > 0:
            print(f"Cache Hit: {saved_tokens_count} scenarios skipped. Tokens saved!")

        df = pd.DataFrame(results)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = os.path.join(self.results_dir, f"experiment_results_{timestamp}.csv")
        df.to_csv(output_path, index=False)
        return df, output_path
