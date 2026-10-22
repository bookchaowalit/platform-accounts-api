"""Identities: who an account belongs to, and how far apart its trust zones must stay."""

import pytest
from inventory_helpers import identity, other_workspace


def test_a_new_identity_is_the_owner_and_active_by_default(client, owner):
    created = identity(client, owner)
    assert created.status_code == 201, created.text
    assert created.json()["relation"] == "self"
    assert created.json()["status"] == "active"


@pytest.mark.parametrize(
    "zone", ["z0-root", "z1-public", "z2-business", "z2-separated"]
)
def test_every_supported_trust_zone_is_accepted(client, owner, zone):
    assert identity(client, owner, trust_zone=zone).status_code == 201


@pytest.mark.parametrize("zone", ["z3-isolated", "z3", "public", ""])
def test_strictly_isolated_and_unknown_zones_are_refused(client, owner, zone):
    # Z3 personas live only in their own vault, never next to the owner's real identity.
    assert identity(client, owner, trust_zone=zone).status_code == 422


def test_trust_zone_is_required(client, owner):
    response = client.post(
        "/v1/identities",
        headers=owner,
        json={"slug": "no-zone", "display_name": "No zone"},
    )
    assert response.status_code == 422


def test_a_slug_is_used_once_per_workspace(client, owner, harness, platform):
    assert identity(client, owner, slug="book").status_code == 201
    again = identity(client, owner, slug="book", display_name="Second")
    assert again.status_code == 409
    assert again.json()["detail"] == {"error": "conflict"}
    elsewhere = identity(client, other_workspace(harness, platform), slug="book")
    assert elsewhere.status_code == 201


def test_slug_is_limited_to_120_characters(client, owner):
    assert identity(client, owner, slug="s" * 121).status_code == 422
    assert identity(client, owner, slug="t" * 120).status_code == 201


@pytest.mark.parametrize("relation", ["friend", "employer", "SELF"])
def test_relation_must_be_self_family_work_or_client(client, owner, relation):
    assert identity(client, owner, relation=relation).status_code == 422


def test_another_workspace_cannot_read_an_identity(client, owner, harness, platform):
    created = identity(client, owner).json()
    stranger = other_workspace(harness, platform)
    assert (
        client.get(f"/v1/identities/{created['id']}", headers=stranger).status_code
        == 404
    )
