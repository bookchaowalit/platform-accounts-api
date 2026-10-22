"""Shared helpers for the accounts domain tests: create records the way the web backend does."""

import uuid
from itertools import count
from typing import Any

_n = count()


def unique(prefix: str) -> str:
    return f"{prefix}-{next(_n)}-{uuid.uuid4().hex[:6]}"


def other_workspace(harness: Any, platform: Any) -> dict[str, str]:
    """A token for a second owner in a workspace of its own, with every permission."""
    actor, workspace = uuid.uuid4(), uuid.uuid4()
    platform.grants[actor] = set(harness.cell.permissions())
    return harness.token(actor, workspace)


def identity(client: Any, owner: dict[str, str], **fields: Any) -> Any:
    payload = {
        "slug": unique("id"),
        "display_name": "Book",
        "trust_zone": "z1-public",
        **fields,
    }
    return client.post("/v1/identities", headers=owner, json=payload)


def mailbox(client: Any, owner: dict[str, str], identity_id: int, **fields: Any) -> Any:
    """Already encrypted by the web backend: a "v1:" envelope and a keyed hash, never an address."""
    payload = {
        "identity_id": identity_id,
        "address_ciphertext": f"v1:{uuid.uuid4().hex}:{uuid.uuid4().hex}:tag",
        "address_hash": uuid.uuid4().hex * 2,
        "address_hint": "b***@example.com",
        "provider": "gmail",
        **fields,
    }
    return client.post("/v1/mailboxes", headers=owner, json=payload)


def account(client: Any, owner: dict[str, str], identity_id: int, **fields: Any) -> Any:
    payload = {
        "identity_id": identity_id,
        "platform": "x",
        "handle": unique("handle"),
        **fields,
    }
    return client.post("/v1/accounts", headers=owner, json=payload)
