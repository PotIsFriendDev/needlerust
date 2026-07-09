import os
import argparse
from dotenv import load_dotenv
from src.client import LLMClient
from src.config import ExperimentPlan
from src.simulator import RustSimulator
from src.report import analyze_all

load_dotenv()


def cmd_run(args):
    if not args.plan:
        raise SystemExit("--plan <path.json> is required for `run`")

    plan = ExperimentPlan.from_json(args.plan)

    # Allow env-var overrides to win over the values baked into the JSON.
    plan.api_key = os.getenv("LLM_API_KEY", plan.api_key)
    plan.base_url = os.getenv("LLM_BASE_URL", plan.base_url)
    plan.model = os.getenv("LLM_MODEL", plan.model)

    client = LLMClient(api_key=plan.api_key, base_url=plan.base_url, model=plan.model)
    simulator = RustSimulator(client=client, results_dir=args.results_dir)

    print(f"Running plan: {plan.name} ({len(plan.generate_scenarios())} scenarios)")
    df, path = simulator.run_experiment(plan, use_cache=not args.no_cache, force_refresh=args.force_refresh)
    print(f"Saved to {path}")
    print(df.head())


def cmd_analyze(args):
    out = analyze_all(args.results_dir, args.output)
    print(f"Wrote aggregate report ({len(out)} chars)")


def main():
    parser = argparse.ArgumentParser(description="NeedleRust: Context Rot Simulation")
    sub = parser.add_subparsers(dest="command")

    p_run = sub.add_parser("run", help="Run an experiment plan from a JSON config")
    p_run.add_argument("--plan", type=str, required=True, help="Path to plan.json")
    p_run.add_argument("--results-dir", default="results")
    p_run.add_argument("--no-cache", action="store_true")
    p_run.add_argument("--force-refresh", action="store_true")
    p_run.set_defaults(func=cmd_run)

    p_an = sub.add_parser("analyze", help="Generate correlation-matrix reports from results/*.csv")
    p_an.add_argument("--results-dir", default="results")
    p_an.add_argument("--output", default=None)
    p_an.set_defaults(func=cmd_analyze)

    args = parser.parse_args()
    if not getattr(args, "command", None):
        parser.print_help()
        raise SystemExit(1)
    args.func(args)


if __name__ == "__main__":
    main()
