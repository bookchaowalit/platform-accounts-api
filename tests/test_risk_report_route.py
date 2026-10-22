"""GET /v1/risk-report over stored records: workspace scope, permissions and what it never returns."""

import uuid

from inventory_helpers import account, identity, mailbox, other_workspace


def report(client, headers):
    response = client.get("/v1/risk-report", headers=headers)
    assert response.status_code == 200, response.text
    return response.json()


def test_an_empty_workspace_has_no_findings(client, owner):
    body = report(client, owner)
    assert body["findings"] == []
    assert body["counts"] == {"high": 0, "medium": 0, "low": 0, "info": 0}
    assert body["totals"] == {"identity": 0, "domain": 0, "mailbox": 0, "account": 0}
    assert body["truncated"] is False


def test_findings_come_from_stored_records_and_name_mailboxes_by_hint(client, owner):
    owner_identity = identity(client, owner).json()["id"]
    created = mailbox(
        client, owner, owner_identity, mfa_method="sms", address_hint="s***@example.com"
    ).json()
    body = report(client, owner)
    weak = [f for f in body["findings"] if f["code"] == "weak_mfa"]
    assert weak == [
        {
            "severity": "high",
            "code": "weak_mfa",
            "subject": {
                "type": "mailbox",
                "id": created["id"],
                "label": "s***@example.com",
            },
            "message": "Second factor is sms; use a passkey or security key.",
        }
    ]
    assert body["counts"]["high"] == 1
    assert body["totals"]["mailbox"] == 1


def test_the_report_never_returns_ciphertext_or_hashes(client, owner):
    owner_identity = identity(client, owner).json()["id"]
    created = mailbox(client, owner, owner_identity, mfa_method="none").json()
    text = client.get("/v1/risk-report", headers=owner).text
    assert created["address_ciphertext"] not in text
    assert created["address_hash"] not in text


def test_a_planned_account_is_not_reported_until_it_is_in_use(client, owner):
    owner_identity = identity(client, owner).json()["id"]
    planned = account(client, owner, owner_identity, mfa_primary="sms").json()
    assert not [
        f
        for f in report(client, owner)["findings"]
        if f["subject"]["id"] == planned["id"]
    ]
    live = account(
        client, owner, owner_identity, mfa_primary="sms", status="active"
    ).json()
    codes = {(f["code"], f["subject"]["id"]) for f in report(client, owner)["findings"]}
    assert ("weak_mfa", live["id"]) in codes


def test_the_report_reads_only_the_callers_workspace(client, owner, harness, platform):
    owner_identity = identity(client, owner).json()["id"]
    mailbox(client, owner, owner_identity, mfa_method="sms")
    stranger = other_workspace(harness, platform)
    body = report(client, stranger)
    assert body["findings"] == []
    assert body["totals"] == {"identity": 0, "domain": 0, "mailbox": 0, "account": 0}


def test_read_permission_on_every_resource_is_required(client, harness, platform):
    actor, workspace = uuid.uuid4(), uuid.uuid4()
    platform.grants[actor] = {
        p for p in harness.cell.permissions() if not p.startswith("accounts.mailbox:")
    }
    response = client.get("/v1/risk-report", headers=harness.token(actor, workspace))
    assert response.status_code == 403
