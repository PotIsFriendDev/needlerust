import json
from dataclasses import dataclass, field
from typing import List, Dict, Any, Union

@dataclass
class Factor:
    name: str
    values: List[Any]

@dataclass
class ExperimentPlan:
    name: str
    model: str
    base_url: str
    api_key: str
    needle: Union[str, List[str]]  # Primary needle or list of needles
    question: str
    system_prompt: str = "You are a helpful assistant."
    factors: List[Factor] = field(default_factory=list)
    global_settings: Dict[str, Any] = field(default_factory=dict)
    prompt_template: str = "Context:\n{context}\n\nQuestion: {question}\nAnswer:"

    @classmethod
    def from_json(cls, json_path: str):
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        factors = [Factor(name=f['name'], values=f['values']) for f in data.get('factors', [])]

        return cls(
            name=data['name'],
            model=data['model'],
            base_url=data['base_url'],
            api_key=data['api_key'],
            system_prompt=data.get('system_prompt', "You are a helpful assistant."),
            needle=data['needle'],
            question=data['question'],
            factors=factors,
            global_settings=data.get('global_settings', {}),
            prompt_template=data.get('prompt_template', "Context:\n{context}\n\nQuestion: {question}\nAnswer:")
        )

    def generate_scenarios(self) -> List[Dict[str, Any]]:
        """
        Generates a Cartesian product of all factors to create an experiment matrix.
        """
        import itertools

        factor_names = [f.name for f in self.factors]
        factor_values = [f.values for f in self.factors]

        combinations = list(itertools.product(*factor_values))

        scenarios = []
        for combo in combinations:
            scenario_params = dict(zip(factor_names, combo))
            scenarios.append(scenario_params)

        return scenarios
