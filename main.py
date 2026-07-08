import os
from dotenv import load_dotenv
from src.client import LLMClient
from src.generators import Scenario
from src.simulator import RustSimulator

load_dotenv()

def main():
    # --- Configuration ---
    API_KEY = os.getenv("LLM_API_KEY", "your-api-key")
    BASE_URL = os.getenv("LLM_BASE_URL", "https://api.openai.com/v1")
    MODEL = os.getenv("LLM_MODEL", "gpt-4o")

    # Fact to hide
    NEEDLE = "The secret code is 12345."
    QUESTION = "What is the secret code?"

    # Define Scenarios to test Context Rust
    # We test different depths (0% to 100%) and different context lengths
    scenarios = []
    for tokens in [4000, 8000, 16000]: # Test different window sizes
        for depth in [0.1, 0.3, 0.5, 0.7, 0.9]: # Test different positions
            scenarios.append(Scenario(
                name=f"depth_{depth}_tokens_{tokens}",
                needle=NEEDLE,
                total_tokens=tokens,
                depth=depth,
                noise=0.0
            ))

    # Add some noisy scenarios for comparison
    for depth in [0.1, 0.5, 0.9]:
        scenarios.append(Scenario(
            name=f"noisy_depth_{depth}",
            needle=NEEDLE,
            total_tokens=8000,
            depth=depth,
            noise=0.2 # 20% noise
        ))

    # Initialize Client & Simulator
    client = LLMClient(api_key=API_KEY, base_url=BASE_URL, model=MODEL)
    simulator = RustSimulator(client=client)

    print(f"Starting NeedleRust simulation for model: {MODEL}...")
    df, path = simulator.run_experiment(scenarios, QUESTION)

    print(f"Simulation complete. Results saved to {path}")
    print(df.head())

if __name__ == "__main__":
    main()
