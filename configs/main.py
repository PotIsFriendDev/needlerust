import os
import argparse
from dotenv import load_dotenv
from src.client import LLMClient
from src.generators import Scenario
from src.simulator import RustSimulator

load_dotenv()

def main():
    parser = argparse.ArgumentParser(description="NeedleRust: Context Rot Simulation")
    parser.add_argument("--tokens", type=int, nargs="+", default=[4000, 8000, 16000], help="List of token lengths to test (e.g. --tokens 4000 8000 32000)")
    parser.add_argument("--depths", type=float, nargs="+", default=[0.1, 0.3, 0.5, 0.7, 0.9], help="List of relative positions to test (e.g. --depths 0.1 0.5 0.9)")
    parser.add_argument("--noise", type=float, nargs="+", default=[0.0, 0.2], help="List of noise levels to test (e.g. --noise 0.0 0.1 0.3)")
    parser.add_argument("--needle", type=str, default="The secret code is 12345.", help="The fact to hide in context")
    parser.add_argument("--question", type=str, default="What is the secret code?", help="The question to ask the LLM")

    args = parser.parse_args()

    # --- Configuration ---
    API_KEY = os.getenv("LLM_API_KEY", "your-api-key")
    BASE_URL = os.getenv("LLM_BASE_URL", "https://api.openai.com/v1")
    MODEL = os.getenv("LLM_MODEL", "gpt-4o")

    NEEDLE = args.needle
    QUESTION = args.question

    # Define Scenarios to test Context Rust
    scenarios = []
    for tokens in args.tokens:
        for depth in args.depths:
            # Run for each noise level specified
            for noise in args.noise:
                scenarios.append(Scenario(
                    name=f"depth_{depth}_tokens_{tokens}_noise_{noise}",
                    needle=NEEDLE,
                    total_tokens=tokens,
                    depth=depth,
                    noise=noise
                ))

    # Initialize Client & Simulator
    client = LLMClient(api_key=API_KEY, base_url=BASE_URL, model=MODEL)
    simulator = RustSimulator(client=client)

    print(f"Starting NeedleRust simulation for model: {MODEL}...")
    print(f"Testing Tokens: {args.tokens}")
    print(f"Testing Depths: {args.depths}")
    print(f"Testing Noise: {args.noise}")

    df, path = simulator.run_experiment(scenarios, QUESTION)

    print(f"Simulation complete. Results saved to {path}")
    print(df.head())

if __name__ == "__main__":
    main()
