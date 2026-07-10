"""
Tests for src/evaluator.Evaluator.check_accuracy.

Background: a previous sweep over kv_fragmentation produced 23 / 450
false-negative rows where the model correctly returned BLUE-OCEAN-7421
but the grader scored 0.0 because the needle was a long multi-fact
string and the model's bare-ID response couldn't match any of the
substring / prefix / digit-fallback checks in the right order.

These tests pin the fix: identifier-fallback must run before the
substring / fact / prefix checks, so a bare-ID response against a
long needle still scores 1.0.
"""

import pytest

from src.evaluator import Evaluator


NEEDLE_V0 = "The vault key is BLUE-OCEAN-7421."

NEEDLE_V1 = (
    "The vault key is BLUE-OCEAN-7421. The access window is 06:00 to 22:00 local. "
    "The second authorization tier requires the rotating token HARRIER-19 published "
    "daily at 05:55. Any entry outside the window triggers a level-3 alert to the "
    "on-call security desk. The most recent false-positive investigation was closed "
    "on 2024-04-22 by Inspector Lin.\n"
    "Key fact: The vault key is BLUE-OCEAN-7421."
)

NEEDLE_V2 = (
    "The vault key is BLUE-OCEAN-7421. The access window is 06:00 to 22:00 local "
    "time, and any entry outside that window is automatically flagged as a level-3 "
    "alert routed to the on-call security desk within 30 seconds. The second "
    "authorization tier requires the rotating token HARRIER-19, which is published "
    "daily at 05:55 to the operator dashboard and is valid only for the following "
    "24 hours. The most recent false-positive investigation was closed on 2024-04-22 "
    "by Inspector Lin after a 14-day review of the access logs covering the prior "
    "quarter. The investigation concluded that 3 of the 7 alerts were triggered by "
    "maintenance personnel using the wrong badge, and the remaining 4 were genuine "
    "test alarms that had not been properly de-registered by the QA team. The "
    "corrective action was to add a mandatory de-registration step to the QA runbook "
    "and to issue a written reminder to all maintenance staff about the correct "
    "badge for the after-hours entrance. The compliance team has scheduled a "
    "follow-up audit for 2024-10-15 to verify that the corrective actions have been "
    "implemented and that no new false-positive pattern has emerged since the "
    "closure date.\n"
    "Key fact: The vault key is BLUE-OCEAN-7421."
)

NEEDLE_SECRET_V1 = (
    "The vault code is 12345, and the entry phrase is 'open sesame'. The combination "
    "was last rotated on 2024-03-15 by Operator-7. The third backup key is held at "
    "the Reykjavik facility. The current shift supervisor prefers the phrase 'bluebird' "
    "when calling in the override. All audit logs are mirrored to a regional cluster "
    "that is not publicly listed in any document.\n"
    "Key fact: The secret code is 12345."
)


@pytest.fixture
def ev():
    return Evaluator("exact")


@pytest.mark.parametrize(
    "needle,response,expected",
    [
        # variant 0 — short needle, all three response styles should pass
        (NEEDLE_V0, "BLUE-OCEAN-7421", 1.0),
        (NEEDLE_V0, "The vault key is BLUE-OCEAN-7421.", 1.0),
        (NEEDLE_V0, "the vault key is blue-ocean-7421", 1.0),
        # variant 1 — long needle. These were the 8 false-negatives.
        (NEEDLE_V1, "BLUE-OCEAN-7421", 1.0),
        (NEEDLE_V1, "The vault key is BLUE-OCEAN-7421.", 1.0),
        (NEEDLE_V1, "BLUE-OCEAN-7421. The access window is 06:00 to 22:00 local.", 1.0),
        # variant 2 — longest needle. These were the 15 false-negatives.
        (NEEDLE_V2, "BLUE-OCEAN-7421", 1.0),
        (NEEDLE_V2, "The vault key is BLUE-OCEAN-7421.", 1.0),
        (
            NEEDLE_V2,
            "The vault key is BLUE-OCEAN-7421. The access window is 06:00 to 22:00 local.",
            1.0,
        ),
        # secondary identifier inside the needle should also count
        (NEEDLE_V1, "HARRIER-19", 1.0),
        (NEEDLE_V2, "HARRIER-19", 1.0),
        # instruction_distance style: pure-digit code as identifier
        (NEEDLE_SECRET_V1, "12345", 1.0),
        (NEEDLE_SECRET_V1, "The secret code is 12345.", 1.0),
    ],
)
def test_bare_or_paragraph_responses_score_1(ev, needle, response, expected):
    assert ev.check_accuracy(needle, response) == expected


@pytest.mark.parametrize(
    "needle,response",
    [
        (NEEDLE_V0, ""),
        (NEEDLE_V1, ""),
        (NEEDLE_V2, ""),
        (NEEDLE_V0, "I don't know"),
        (NEEDLE_V1, "I don't know"),
        (NEEDLE_V2, "I don't know"),
        # identifier that is NOT in the needle must not match
        (NEEDLE_V1, "RED-MOUNTAIN-9999"),
        (NEEDLE_V2, "OPEN-SESAME"),
        # 2024 as a year must not masquerade as an identifier match
        # (digit fallback is fine here — 4 digits and the needle contains
        # 2024-04-22 — but for the V1/V2 needles the ID is 7421, so a
        # response of just "2024" should NOT score, because the
        # identifier is 7421, not 2024)
        (NEEDLE_V1, "2024"),
        (NEEDLE_V2, "2024"),
    ],
)
def test_non_matching_responses_score_0(ev, needle, response):
    assert ev.check_accuracy(needle, response) == 0.0


def test_three_real_needles_share_grade_with_bare_response(ev):
    """The bug surfaced as: same bare response, three different scores
    across variants. After the fix, all three must agree at 1.0."""
    bare = "BLUE-OCEAN-7421"
    scores = [
        ev.check_accuracy(NEEDLE_V0, bare),
        ev.check_accuracy(NEEDLE_V1, bare),
        ev.check_accuracy(NEEDLE_V2, bare),
    ]
    assert scores == [1.0, 1.0, 1.0]


def test_extract_identifiers_pure_uppercase_runs():
    """Sanity: helper must not return ordinary English words."""
    from src.evaluator import _extract_identifiers

    needle = (
        "The vault key is BLUE-OCEAN-7421. The second token is HARRIER-19. "
        "The most recent false-positive was closed in 2024 by Inspector Lin."
    )
    ids = _extract_identifiers(needle)
    # BLUE-OCEAN-7421 and HARRIER-19 must be present
    assert "BLUE-OCEAN-7421" in ids
    assert "HARRIER-19" in ids
    # 2024 is exactly 4 digits, and `\b[A-Z0-9]+` matches it as an
    # identifier. It WILL be returned, but since 2024 is not the key
    # being graded and the response must also contain the true key,
    # the grader's behavior depends on whether the response contains
    # 2024. This test only asserts the helper is well-behaved for
    # the obvious IDs.
    # Common English words must NOT be returned.
    for forbidden in ("The", "vault", "key", "Inspector", "Lin", "and", "is"):
        assert forbidden not in ids, f"{forbidden!r} should not be an identifier"


# ---- Wording-consistency guard ---------------------------------------------
# History: the instruction_distance sweep once had variant 1/2 needles
# starting with "The vault code is 12345..." while the question asked
# "What is the secret code?". Models defaulted to the "secret code"
# template, so ~91% of variant 1/2 responses used the wrong wording
# and were graded 0 — a pure wording-bias false negative.
#
# Two regressions to guard against:
#   1. The needle and question drift apart in wording again.
#   2. The grader becomes brittle to the *exact* wording and breaks
#      when the needle says "secret" but the model says "the code".
# Tests below pin BOTH the needle wording (load from config) and the
# grader's robustness to wording variation.

def test_instruction_distance_needle_wording_matches_question():
    """The needle for every variant must use the same wording the
    question asks about, otherwise models default to the question's
    wording and the grader gets fooled by phrasing bias."""
    import json
    from pathlib import Path

    cfg_path = Path("configs/instruction_distance.json")
    if not cfg_path.exists():
        pytest.skip("config not present in cwd")
    with cfg_path.open(encoding="utf-8") as f:
        cfg = json.load(f)

    question = cfg["question"].lower()
    needles = cfg["needle"]
    if not isinstance(needles, list):
        needles = [needles]

    # Question asks about a "secret code"; every needle variant must
    # use the same wording so the grader's needle-substring path is
    # exercised by a model that follows the question.
    if "secret code" in question:
        for i, n in enumerate(needles):
            assert "secret code" in n.lower(), (
                f"variant {i} of instruction_distance.json does not mention "
                f"'secret code' even though the question asks about it: {n[:80]!r}"
            )


@pytest.mark.parametrize(
    "needle,response,expected",
    [
        # bare ID
        ("The secret code is 12345.", "12345", 1.0),
        ("The secret code is 12345, and the entry phrase is 'open sesame'.",
         "12345", 1.0),
        # canonical wording
        ("The secret code is 12345.", "The secret code is 12345.", 1.0),
        ("The secret code is 12345, and the entry phrase is 'open sesame'.",
         "The secret code is 12345.", 1.0),
        # model paraphrases with "the code" instead of "secret code" —
        # identifier-fallback must catch this
        ("The secret code is 12345.", "The code is 12345.", 1.0),
        ("The secret code is 12345, and the entry phrase is 'open sesame'.",
         "The code is 12345.", 1.0),
        # markdown-wrapped
        ("The secret code is 12345.", "The secret code is **12345**.", 1.0),
    ],
)
def test_instruction_distance_grader_is_wording_robust(ev, needle, response, expected):
    """Grader must accept any phrasing that contains the right ID,
    not require the exact sentence from the needle."""
    assert ev.check_accuracy(needle, response) == expected
