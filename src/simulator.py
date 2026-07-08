import pandas as pd
import os
import json
import hashlib
from datetime import datetime
from typing import List, Dict, Any, Union
from .client import LLMClient
from .generators import ContextAssembler
from .evaluator import Evaluator
from .config import ExperimentPlan
from .turn_manager import TurnManager
from tqdm import tqdm

class RustSimulator:
    def __init__(self, client: LLMClient, results_dir: str = "results", cache_file: str = "cache.json"):
        self.client = client
        self.results_dir = results_dir
        self.cache_file = os.path.join(results_dir, cache_file)
        self.assembler = ContextAssembler()
        self.evaluator = Evaluator()
        self.turn_manager = TurnManager()

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

    def _generate_scenario_hash(self, plan: ExperimentPlan, params: Dict[str, Any], question: str) -> str:
        # Create a unique hash based on all factors that affect the output
        param_str = json.dumps(params, sort_keys=True)
        input_str = f"{plan.name}|{plan.needle}|{param_str}|{question}"
        return hashlib.sha256(input_str.encode()).hexdigest()

    def run_experiment(self, plan: ExperimentPlan, use_cache: bool = True, force_refresh: bool = False):
        scenarios = plan.generate_scenarios()
        results = []
        saved_tokens_count = 0

        for params in tqdm(scenarios, desc=f"Running experiment: {plan.name}"):
            scenario_hash = self._generate_scenario_hash(plan, params, plan.question)

            # Update evaluator method based on plan if present
            eval_method = params.get('eval_method', 'exact')
            self.evaluator.method = eval_method

            # 1. Check Cache
            if use_cache and not force_refresh and scenario_hash in self.cache:
                cached_res = self.cache[scenario_hash]
                results.append(cached_res)
                saved_tokens_count += 1
                continue

            # 2. Generate Context
            needle_input = plan.needle[0] if isinstance(plan.needle, list) else plan.needle
            context = self.assembler.assemble(needle_input, params)

            # Handle Multi-turn Simulation
            if 'turns' in params:
                self.turn_manager.clear()
                self.turn_manager.simulate_turns(params['turns'])
                history = self.turn_manager.get_full_context()
                context = f"{history}\n\n{context}"

            # 3. Query LLM
            prompt = plan.prompt_template.format(context=context, question=plan.question)
            response = self.client.get_completion(prompt)

            # 4. Evaluate
            accuracy = self.evaluator.check_accuracy(plan.needle, response)

            res_data = {
                "scenario": plan.name,
                **params,
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
        output_path = os.path.join(self.results_dir, f"experiment_{plan.name}_{timestamp}.csv")
        df.to_csv(output_path, index=False)
        return df, output_path
