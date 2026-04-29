from __future__ import annotations

from microservices.telemetry_service.realtime import (
    hash_connect_token,
    subscription_matches_tags,
    verify_connect_token,
)


def test_hash_connect_token_is_stable():
    token = "connect-token-123"

    assert hash_connect_token(token) == hash_connect_token(token)


def test_verify_connect_token_accepts_matching_hash():
    token = "connect-token-123"
    token_hash = hash_connect_token(token)

    assert verify_connect_token(token, token_hash) is True


def test_verify_connect_token_rejects_non_matching_hash():
    token = "connect-token-123"
    other_hash = hash_connect_token("different-token")

    assert verify_connect_token(token, other_hash) is False


def test_subscription_matches_tags_requires_subset_match():
    assert subscription_matches_tags(
        {"site": "lab", "rack": "r1"},
        {"site": "lab", "rack": "r1", "region": "cn"},
    )


def test_subscription_matches_tags_rejects_missing_or_mismatched_tags():
    assert not subscription_matches_tags({"site": "lab"}, {})
    assert not subscription_matches_tags({"site": "lab"}, {"site": "prod"})
