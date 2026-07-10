"""
Tests for LLMClient.get_completion error handling and report.analyze
infrastructure-failure exclusion.

Background: a prior output_pressure sweep showed 2 / 36 empty
responses graded 0.0 indistinguishable from "model answered wrong".
`client.get_completion` silently swallowed API exceptions, returning
"". The fix: return a (content, error) tuple and surface the error
through the CSV's `error` column; `report.analyze` then excludes
those rows from the accuracy mean.
"""

import csv
import io
import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from src.client import LLMClient
from src.report import analyze


# ---- client.get_completion error pass-through --------------------------------

class _FakeAPIError(Exception):
    """Mimics an openai.APIError with a single-line message."""


def _mock_openai_client_that_raises(exc: Exception):
    """Return a stand-in for openai.OpenAI whose chat.completions.create raises."""
    fake = MagicMock()
    fake.chat.completions.create.side_effect = exc
    return fake


def test_get_completion_returns_content_and_empty_error_on_success():
    fake_response = MagicMock()
    fake_response.choices = [MagicMock()]
    fake_response.choices[0].message.content = "The secret code is 12345."
    fake = MagicMock()
    fake.chat.completions.create.return_value = fake_response

    with patch("src.client.OpenAI", return_value=fake):
        client = LLMClient(api_key="x", base_url="y", model="gpt-4o")
        content, error = client.get_completion("prompt", system_prompt="sys")

    assert content == "The secret code is 12345."
    assert error == ""


def test_get_completion_returns_short_error_string_on_exception():
    """An API failure must surface as a non-empty `error` string,
    not be silently turned into an empty content string."""
    fake = _mock_openai_client_that_raises(
        _FakeAPIError("Connection timeout after 30s")
    )
    with patch("src.client.OpenAI", return_value=fake):
        client = LLMClient(api_key="x", base_url="y", model="gpt-4o")
        content, error = client.get_completion("prompt", system_prompt="sys")

    assert content == ""
    assert error != ""
    # Must include the exception class name and first line of the message
    # so a reader of the CSV can tell what went wrong.
    assert "FakeAPIError" in error
    assert "Connection timeout" in error


def test_get_completion_empty_content_but_no_error_returns_zero_error():
    """When the API succeeds but the model returns no content (rare but
    possible for some providers), the call is not an infrastructure
    failure and `error` should remain empty."""
    fake_response = MagicMock()
    fake_response.choices = [MagicMock()]
    fake_response.choices[0].message.content = None
    fake = MagicMock()
    fake.chat.completions.create.return_value = fake_response

    with patch("src.client.OpenAI", return_value=fake):
        client = LLMClient(api_key="x", base_url="y", model="gpt-4o")
        content, error = client.get_completion("prompt", system_prompt="sys")

    assert content == ""
    assert error == ""


# ---- report.analyze infrastructure-failure exclusion ------------------------

def _write_csv(tmpdir, rows):
    """Write a minimal experiment CSV with the given row dicts."""
    path = Path(tmpdir) / "experiment_test.csv"
    fields = list(rows[0].keys())
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    return path


def _make_row(accuracy, error=""):
    return {
        "scenario": "test_sweep",
        "total_tokens": 8000,
        "output_pressure": 0,
        "needle_variant": 0,
        "seed": 1,
        "accuracy": accuracy,
        "response": "The secret code is 12345." if not error else "",
        "error": error,
    }


def test_analyze_excludes_rows_with_error_column(tmp_path):
    """A row with a non-empty `error` column must be excluded from
    the accuracy mean. Without this fix, an API timeout counts as
    a 'model was wrong' false negative."""
    rows = [_make_row(1.0) for _ in range(8)]
    rows += [_make_row(0.0, error="FakeAPIError: timeout")]
    rows += [_make_row(1.0) for _ in range(1)]
    path = _write_csv(tmp_path, rows)
    text = analyze(str(path))

    # 9 graded rows (8 + 1) all scoring 1.0 -> mean 1.000
    assert "Mean accuracy: **1.000**" in text
    # 1 infrastructure failure must be reported separately
    assert "Infrastructure failures (skipped from accuracy): **1**" in text


def test_analyze_falls_back_to_empty_response_when_no_error_column(tmp_path):
    """Old CSVs (pre-error-column) used empty response as a proxy
    for 'infrastructure failure'. We must keep that working so we
    can re-analyze the historical sweep."""
    rows = [_make_row(1.0) for _ in range(8)]
    rows += [{
        "scenario": "test_sweep",
        "total_tokens": 8000,
        "output_pressure": 0,
        "needle_variant": 0,
        "seed": 1,
        "accuracy": 0.0,
        "response": "",  # empty
        # no 'error' column at all
    }]
    # Drop the error column entirely to simulate a pre-fix CSV.
    for r in rows:
        r.pop("error", None)
    path = _write_csv(tmp_path, rows)
    text = analyze(str(path))
    assert "Mean accuracy: **1.000**" in text
    assert "Infrastructure failures (skipped from accuracy): **1**" in text


def test_analyze_does_not_count_error_as_a_factor(tmp_path):
    """The new `error` column should not appear in the per-factor
    breakdown — it's metadata, not an experimental factor."""
    rows = [_make_row(1.0) for _ in range(3)]
    rows += [_make_row(0.0, error="X"), _make_row(0.0, error="Y"), _make_row(0.0, error="X")]
    path = _write_csv(tmp_path, rows)
    text = analyze(str(path))
    # The Per-factor breakdown header is included but 'error' must
    # not appear in the table contents.
    assert "## Per-factor breakdown" in text
    assert "| error |" not in text


# ---- Config seed expansion --------------------------------------------------

def test_all_configs_have_at_least_10_seeds():
    """Seed factor must be at least 10 levels across all configs so
    per-cell statistics have enough sample size to be meaningful."""
    import json
    configs = [
        "configs/instruction_distance.json",
        "configs/kv_fragmentation.json",
        "configs/output_pressure.json",
        "configs/task_complexity.json",
    ]
    for path in configs:
        with open(path, encoding="utf-8") as f:
            cfg = json.load(f)
        seed_factor = next(f for f in cfg["factors"] if f["name"] == "seed")
        assert len(seed_factor["values"]) >= 10, (
            f"{path} has only {len(seed_factor['values'])} seed levels"
        )
