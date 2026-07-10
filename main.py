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

    # CLI overrides beat env vars: lets us run the same plan against a
    # baseline model (e.g. deepseek-chat vs deepseek-reasoner) without
    # touching .env. See todo §10 P-D.
    if getattr(args, 'model_override', None):
        plan.model = args.model_override
    if getattr(args, 'base_url_override', None):
        plan.base_url = args.base_url_override
    if getattr(args, 'api_key_override', None):
        plan.api_key = args.api_key_override

    client = LLMClient(api_key=plan.api_key, base_url=plan.base_url, model=plan.model)
    simulator = RustSimulator(client=client, results_dir=args.results_dir)

    print(f"Running plan: {plan.name} ({len(plan.generate_scenarios())} scenarios)")
    df, path = simulator.run_experiment(plan, use_cache=not args.no_cache, force_refresh=args.force_refresh)
    print(f"Saved to {path}")
    print(df.head())


def cmd_analyze(args):
    excludes = None
    if getattr(args, 'exclude', None):
        excludes = [p.strip() for p in args.exclude.split(',') if p.strip()]
    out = analyze_all(args.results_dir, args.output, exclude_globs=excludes)
    print(f"Wrote aggregate report ({len(out)} chars)")


def main():
    parser = argparse.ArgumentParser(description="NeedleRust: Context Rot Simulation")
    sub = parser.add_subparsers(dest="command")

    p_run = sub.add_parser("run", help="Run an experiment plan from a JSON config")
    p_run.add_argument("--plan", type=str, required=True, help="Path to plan.json")
    p_run.add_argument("--results-dir", default="results")
    p_run.add_argument("--no-cache", action="store_true")
    p_run.add_argument("--force-refresh", action="store_true")
    p_run.add_argument("--model-override", type=str, default=None,
                       help="Override plan.model (CLI beats env var).")
    p_run.add_argument("--base-url-override", type=str, default=None,
                       help="Override plan.base_url (CLI beats env var).")
    p_run.add_argument("--api-key-override", type=str, default=None,
                       help="Override plan.api_key (CLI beats env var).")
    p_run.set_defaults(func=cmd_run)

    p_an = sub.add_parser("analyze", help="Generate correlation-matrix reports from results/*.csv")
    p_an.add_argument("--results-dir", default="results")
    p_an.add_argument("--output", default=None)
    p_an.add_argument("--exclude", type=str, default=None,
                     help="Comma-separated glob patterns to exclude from analysis "
                          "(e.g. '*_20260709_224609.csv' to drop a failed run).")
    p_an.set_defaults(func=cmd_analyze)

    args = parser.parse_args()
    if not getattr(args, "command", None):
        parser.print_help()
        raise SystemExit(1)
    args.func(args)


if __name__ == "__main__":
    main()
