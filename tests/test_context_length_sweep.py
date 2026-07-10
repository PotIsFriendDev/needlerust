"""
Smoke tests for the context_length_sweep plan.

Validates:
  - Plan parses and produces the expected scenario count
    (4 lengths × 10 seeds = 40).
  - The generated context length matches the target within ±5%
    for every total_tokens value, including the 128k upper bound.
  - The needle appears verbatim in the assembled context for
    every scenario, so a model failure to recall it cannot be
    blamed on the assembler dropping it.
  - Catches silent regressions in StructureAssembler / plan
    factors that would invalidate the entire length-attention
    experiment.
"""

import json
from pathlib import Path

import pytest

from src.config import ExperimentPlan
from src.generators import ContextAssembler


PLAN_PATH = Path("configs/context_length_sweep.json")
LENGTHS = [4096, 16384, 65536, 131072]
SEEDS = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]


@pytest.fixture
def plan():
    if not PLAN_PATH.exists():
        pytest.skip(f"{PLAN_PATH} not present in cwd")
    return ExperimentPlan.from_json(str(PLAN_PATH))


def test_plan_scenario_count(plan):
    """4 lengths × 10 seeds = 40 scenarios. If this drifts, somebody
    added or removed a factor value and the experiment is no longer
    the 'length-only' sweep we expect."""
    scenarios = plan.generate_scenarios()
    assert len(scenarios) == len(LENGTHS) * len(SEEDS), (
        f"expected {len(LENGTHS) * len(SEEDS)} scenarios, got {len(scenarios)}"
    )


def test_plan_factor_cardinality(plan):
    """Pin the explicit factor list. Adding an extra factor (e.g.
    noise, output_pressure) without thinking would invalidate the
    'length-only' assumption of this sweep."""
    factor_names = sorted(f.name for f in plan.factors)
    assert factor_names == sorted([
        "total_tokens",
        "depth",
        "fragment_count",
        "needle_fragment_index",
        "gap_tokens",
        "needle_variant",
        "seed",
    ]), f"plan factors drifted: {factor_names}"


def test_plan_lengths_cover_low_to_max(plan):
    """Length values must include 4096 (the small-scale ceiling we
    keep hitting in other sweeps) AND 131072 (the OpenAI gpt-4o
    hard context limit). Removing either end makes the curve
    uninformative."""
    length_factor = next(f for f in plan.factors if f.name == "total_tokens")
    assert 4096 in length_factor.values
    assert 131072 in length_factor.values


def test_plan_seed_count_at_least_10(plan):
    """Reuses the global minimum-sample guarantee so a future edit
    that drops seed back to 3 is caught here too."""
    seed_factor = next(f for f in plan.factors if f.name == "seed")
    assert len(seed_factor.values) >= 10


def test_assembled_context_length_matches_target(plan):
    """For every total_tokens, the assembled context must be within
    ±5% of the target character budget. If this drifts, the
    experiment is no longer measuring 'attention at length X' —
    it's measuring attention at some unknown shorter length."""
    assembler = ContextAssembler()
    for t in LENGTHS:
        params = {
            "total_tokens": t,
            "depth": 0.5,
            "fragment_count": 1,
            "gap_tokens": 0,
            "needle_fragment_index": 0.5,
        }
        context = assembler.assemble(plan.needle[0], params)
        target_chars = t * 4
        actual_chars = len(context)
        err = abs(actual_chars - target_chars) / target_chars
        assert err <= 0.05, (
            f"length {t}: actual={actual_chars} target={target_chars} err={err:.2%}"
        )


def test_needle_present_in_every_context(plan):
    """The needle must be embedded verbatim. If a future change to
    StructureAssembler drops it, the resulting accuracy numbers
    will all be 0 and the length-attention hypothesis will be
    untestable."""
    needle_text = plan.needle[0]
    assembler = ContextAssembler()
    for t in LENGTHS:
        params = {
            "total_tokens": t,
            "depth": 0.5,
            "fragment_count": 1,
            "gap_tokens": 0,
            "needle_fragment_index": 0.5,
        }
        context = assembler.assemble(needle_text, params)
        assert needle_text in context, (
            f"needle missing from assembled context at total_tokens={t}"
        )


def test_all_factors_besides_total_tokens_are_pinned(plan):
    """This sweep's whole point is to isolate `total_tokens` as the
    only varying factor. Every other factor must have a single
    value (or be absent and default to a benign value) so a
    Pearson r against accuracy later can be attributed cleanly."""
    for factor in plan.factors:
        if factor.name == "total_tokens" or factor.name == "seed":
            continue
        assert len(factor.values) == 1, (
            f"factor {factor.name!r} has {len(factor.values)} values; "
            f"context_length_sweep requires it pinned to a single value "
            f"so the length effect isn't confounded"
        )
