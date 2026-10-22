"""Mailboxes: addresses are stored only as ciphertext plus a keyed hash, and the hash is unique."""

import pytest
from inventory_helpers import identity, mailbox, other_workspace


@pytest.fixture
def owner_identity(client, owner):
    return identity(client, owner).json()["id"]


def test_an_encrypted_mailbox_is_stored_with_safe_defaults(
    client, owner, owner_identity
):
    created = mailbox(client, owner, owner_identity)
    assert created.status_code == 201, created.text
    row = created.json()
    assert row["kind"] == "mailbox"
    assert row["mfa_method"] == "unknown"
    assert row["security_keys"] == 0
    assert row["recovery_phone"] is False
    assert row["status"] == "active"


def test_a_plaintext_address_in_the_ciphertext_is_refused(
    client, owner, owner_identity
):
    response = mailbox(
        client, owner, owner_identity, address_ciphertext="someone@example.com"
    )
    assert response.status_code == 422
    assert response.json()["detail"] == {"error": "invalid_value"}


def test_a_plaintext_address_in_the_hash_is_refused(client, owner, owner_identity):
    response = mailbox(
        client, owner, owner_identity, address_hash="someone@example.com"
    )
    assert response.status_code == 422
    assert response.json()["detail"] == {"error": "invalid_value"}


def test_the_same_address_hash_is_stored_once_per_workspace(
    client, owner, owner_identity, harness, platform
):
    assert (
        mailbox(client, owner, owner_identity, address_hash="h" * 64).status_code == 201
    )
    again = mailbox(client, owner, owner_identity, address_hash="h" * 64)
    assert again.status_code == 409
    stranger = other_workspace(harness, platform)
    their_identity = identity(client, stranger).json()["id"]
    assert (
        mailbox(client, stranger, their_identity, address_hash="h" * 64).status_code
        == 201
    )


def test_a_mailbox_must_belong_to_an_identity(client, owner):
    response = client.post(
        "/v1/mailboxes",
        headers=owner,
        json={
            "address_ciphertext": "v1:a:b:c",
            "address_hash": "e" * 64,
            "address_hint": "b***@example.com",
            "provider": "gmail",
        },
    )
    assert response.status_code == 422


def test_security_keys_are_counted_from_0_to_20(client, owner, owner_identity):
    assert mailbox(client, owner, owner_identity, security_keys=21).status_code == 422
    assert mailbox(client, owner, owner_identity, security_keys=-1).status_code == 422
    assert mailbox(client, owner, owner_identity, security_keys=20).status_code == 201


def test_a_recovery_mailbox_must_exist(client, owner, owner_identity):
    response = mailbox(client, owner, owner_identity, recovery_mailbox_id=999_999_999)
    assert response.status_code == 422
    assert response.json()["detail"] == {"error": "reference_not_found"}


def test_mfa_method_must_be_a_known_kind(client, owner, owner_identity):
    assert mailbox(client, owner, owner_identity, mfa_method="email").status_code == 422
