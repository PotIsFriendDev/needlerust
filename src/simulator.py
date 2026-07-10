import pandas as pd
import os
import json
import hashlib
from datetime import datetime
from typing import List, Dict, Any, Union
from .client import LLMClient
from .generators import ContextAssembler, resolve_task_template
from .evaluator import Evaluator
from .config import ExperimentPlan
from .turn_manager import TurnManager
from tqdm import tqdm


def _build_pressure_instruction(pressure: int) -> str:
    if pressure <= 0:
        return ""
    return (
        f"Output pressure is enabled. Continue writing for at least "
        f"{pressure} more tokens after your final answer. You may elaborate "
        f"on the context, repeat key facts, or fill with reasoned analysis, "
        f"but you MUST keep producing tokens until the budget is exhausted."
    )


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
        param_str = json.dumps(params, sort_keys=True, default=str)
        input_str = f"{plan.name}|{plan.needle}|{param_str}|{question}"
        return hashlib.sha256(input_str.encode()).hexdigest()

    def run_experiment(self, plan: ExperimentPlan, use_cache: bool = True, force_refresh: bool = False):
        scenarios = plan.generate_scenarios()
        results = []
        saved_tokens_count = 0

        for params in tqdm(scenarios, desc=f"Running experiment: {plan.name}"):
            scenario_hash = self._generate_scenario_hash(plan, params, plan.question)

            eval_method = params.get('eval_method', 'exact')
            self.evaluator.method = eval_method

            if use_cache and not force_refresh and scenario_hash in self.cache:
                cached_res = self.cache[scenario_hash]
                results.append(cached_res)
                saved_tokens_count += 1
                continue

            # 1. Pick the right prompt template based on the task-complexity
            # ladder; fall back to the plan's default.
            task_complexity = params.get('task_complexity')
            prompt_template = (
                resolve_task_template(task_complexity, plan.prompt_template)
                if task_complexity else plan.prompt_template
            )

            # 2. Generate Context
            # When plan.needle is a list, params['needle_variant'] (0-based)
            # selects which needle to embed. This is the lever for the
            # needle-length tiers in P-B: short / medium / long needles
            # stored in the same plan, selected per scenario.
            if isinstance(plan.needle, list):
                variant = int(params.get('needle_variant', 0))
                variant = max(0, min(variant, len(plan.needle) - 1))
                needle_input = plan.needle[variant]
            else:
                needle_input = plan.needle
            context = self.assembler.assemble(needle_input, params)

            if 'turns' in params:
                self.turn_manager.clear()
                self.turn_manager.simulate_turns(params['turns'])
                history = self.turn_manager.get_full_context()
                context = f"{history}\n\n{context}"

            # 3. Query LLM (with optional output-length pressure)
            prompt = prompt_template.format(context=context, question=plan.question)
            output_pressure = int(params.get('output_pressure', 0))
            max_tokens = params.get('max_tokens')
            if output_pressure > 0 and (max_tokens is None or max_tokens < output_pressure + 256):
                # Reserve a headroom over the requested pressure so the model
                # actually has room to ramble.
                max_tokens = output_pressure + 256
            pressure_instruction = _build_pressure_instruction(output_pressure)
            response = self.client.get_completion(
                prompt,
                system_prompt=plan.system_prompt,
                max_tokens=max_tokens,
                pressure_instruction=pressure_instruction,
            )

            # 4. Evaluate — pass the actually-embedded needle so multi-tier
            # needle plans evaluate against the right fact.
            accuracy = self.evaluator.check_accuracy(needle_input, response)

            res_data = {
                "scenario": plan.name,
                **params,
                "accuracy": accuracy,
                "response": response,
            }

            results.append(res_data)

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
