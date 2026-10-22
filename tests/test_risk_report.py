"""The risk report: pure rules first, then the route with its permissions and the storage guards."""

from datetime import date

from cellkit.testing import ISSUER  # noqa: F401  (fixtures come from conftest)
from solo_accounts.routes import analyse

TODAY = date(2026, 10, 10)


def ident(i, zone="z1-public", group=None, relation="self"):
    return {
        "id": i,
        "slug": f"id-{i}",
        "trust_zone": zone,
        "isolation_group": group,
        "relation": relation,
    }


def mail(
    i,
    identity=1,
    recovery=None,
    keys=0,
    mfa="security-key",
    status="active",
    domain=None,
    reviewed=TODAY,
    kind="mailbox",
):
    return {
        "id": i,
        "identity_id": identity,
        "recovery_mailbox_id": recovery,
        "security_keys": keys,
        "mfa_method": mfa,
        "status": status,
        "domain_id": domain,
        "last_reviewed_on": reviewed,
        "kind": kind,
        "address_hint": f"m{i}***",
    }


def acct(
    i,
    identity=1,
    login=None,
    admin=None,
    mfa="passkey",
    status="active",
    social="none",
    phone=False,
    kind="profile",
):
    return {
        "id": i,
        "identity_id": identity,
        "login_mailbox_id": login,
        "admin_account_id": admin,
        "mfa_primary": mfa,
        "status": status,
        "social_login": social,
        "phone_bound": phone,
        "platform": "x",
        "handle": f"h{i}",
        "kind": kind,
    }


def codes(findings):
    return {(f["code"], f["subject"]["id"]) for f in findings}


def test_recovery_hub_without_two_keys_is_high():
    mails = [mail(1, keys=1)] + [mail(i, recovery=1) for i in range(2, 5)]
    out = analyse([ident(1)], [], mails, [], TODAY)
    assert ("recovery_hub_unprotected", 1) in codes(out)
    assert out[0]["severity"] == "high"


def test_recovery_hub_with_two_keys_is_info():
    mails = [mail(1, keys=2)] + [mail(i, recovery=1) for i in range(2, 5)]
    out = analyse([ident(1)], [], mails, [], TODAY)
    assert ("recovery_hub", 1) in codes(out)
    assert all(f["severity"] != "high" for f in out)


def test_recovery_cycle_and_dead_recovery():
    mails = [
        mail(1, recovery=2),
        mail(2, recovery=1),
        mail(3, recovery=4),
        mail(4, status="deleted"),
    ]
    found = codes(analyse([ident(1)], [], mails, [], TODAY))
    assert ("recovery_cycle", 1) in found
    assert ("recovery_cycle", 2) in found
    assert ("recovery_not_live", 3) in found


def test_recovery_through_work_mailbox():
    found = codes(
        analyse(
            [ident(1), ident(2, relation="work")],
            [],
            [mail(1, recovery=2), mail(2, identity=2)],
            [],
            TODAY,
        )
    )
    assert ("recovery_via_work", 1) in found


def test_weak_mfa():
    found = codes(
        analyse([ident(1)], [], [mail(1, mfa="sms")], [acct(9, mfa="none")], TODAY)
    )
    assert ("weak_mfa", 1) in found
    assert ("weak_mfa", 9) in found


def test_separated_brand_crossings():
    identities = [
        ident(1, group="book"),
        ident(2, zone="z2-separated", group="brand-a"),
    ]
    mails = [mail(1, identity=1), mail(2, identity=2)]
    accounts = [
        acct(10, identity=1),
        acct(11, identity=2, login=1, admin=10, social="google", phone=True),
    ]
    found = codes(analyse(identities, [], mails, accounts, TODAY))
    for code in (
        "zone_crossing_login",
        "zone_crossing_admin",
        "social_login_separated",
        "phone_bound_separated",
    ):
        assert (code, 11) in found
    clean = codes(
        analyse(identities, [], mails, [acct(12, identity=2, login=2)], TODAY)
    )
    assert not any(subject == 12 for _, subject in clean)


def test_domain_release_with_mail_still_on_it():
    domains = [
        {
            "id": 5,
            "name": "old.example",
            "status": "active",
            "auto_renew": False,
            "renews_on": date(2026, 11, 1),
        }
    ]
    out = analyse([ident(1)], domains, [mail(1, domain=5)], [acct(2, login=1)], TODAY)
    found = codes(out)
    assert ("domain_release_takeover", 5) in found
    assert ("domain_expiring", 5) in found


def test_domain_release_counts_mailboxes_marked_for_deletion():
    domains = [
        {
            "id": 5,
            "name": "old.example",
            "status": "releasing",
            "auto_renew": True,
            "renews_on": None,
        }
    ]
    found = codes(
        analyse([ident(1)], domains, [mail(1, domain=5, status="to-delete")], [], TODAY)
    )
    assert ("domain_release_takeover", 5) in found
    gone = codes(
        analyse([ident(1)], domains, [mail(1, domain=5, status="deleted")], [], TODAY)
    )
    assert ("domain_release_takeover", 5) not in gone


def test_login_mailbox_marked_for_deletion_and_review():
    out = analyse(
        [ident(1)],
        [],
        [mail(1, status="to-delete"), mail(2, reviewed=None)],
        [acct(3, login=1)],
        TODAY,
    )
    found = codes(out)
    assert ("login_mailbox_not_live", 3) in found
    assert ("review_overdue", 2) in found


def test_route_requires_read_on_every_resource(client, owner, harness):
    response = client.get("/v1/risk-report", headers=owner)
    assert response.status_code == 200
    body = response.json()
    assert set(body["totals"]) == {"identity", "domain", "mailbox", "account"}
    assert "findings" in body
    assert client.get("/v1/risk-report").status_code == 401


def test_plaintext_address_and_isolated_zone_are_refused(client, owner):
    identity = client.post(
        "/v1/identities",
        headers=owner,
        json={"slug": "book", "display_name": "Book", "trust_zone": "z1-public"},
    )
    assert identity.status_code == 201, identity.text
    z3 = client.post(
        "/v1/identities",
        headers=owner,
        json={"slug": "persona", "display_name": "P", "trust_zone": "z3-isolated"},
    )
    assert z3.status_code == 422
    plain = client.post(
        "/v1/mailboxes",
        headers=owner,
        json={
            "identity_id": identity.json()["id"],
            "address_ciphertext": "someone@example.com",
            "address_hash": "a" * 64,
            "address_hint": "s***@example.com",
            "provider": "gmail",
        },
    )
    assert plain.status_code in (409, 422), plain.text
    ok = client.post(
        "/v1/mailboxes",
        headers=owner,
        json={
            "identity_id": identity.json()["id"],
            "address_ciphertext": "v1:abc:def:ghi",
            "address_hash": "b" * 64,
            "address_hint": "s***@example.com",
            "provider": "gmail",
        },
    )
    assert ok.status_code == 201, ok.text


def test_web_style_edit_clears_optional_fields(client, owner):
    """The web sends every field on an edit; empty optional ones arrive as null."""
    identity = client.post(
        "/v1/identities",
        headers=owner,
        json={"slug": "book2", "display_name": "Book", "trust_zone": "z1-public"},
    ).json()
    hub = client.post(
        "/v1/mailboxes",
        headers=owner,
        json={
            "identity_id": identity["id"],
            "address_ciphertext": "v1:a:b:c",
            "address_hash": "c" * 64,
            "address_hint": "h***@example.com",
            "provider": "gmail",
        },
    ).json()
    box = client.post(
        "/v1/mailboxes",
        headers=owner,
        json={
            "identity_id": identity["id"],
            "address_ciphertext": "v1:d:e:f",
            "address_hash": "d" * 64,
            "address_hint": "x***@example.com",
            "provider": "gmail",
            "recovery_mailbox_id": hub["id"],
            "notes": "n",
        },
    ).json()
    patch = client.patch(
        f"/v1/mailboxes/{box['id']}",
        headers=owner,
        json={
            "identity_id": identity["id"],
            "provider": "gmail",
            "kind": "mailbox",
            "domain_id": None,
            "forwards_to_id": None,
            "recovery_mailbox_id": None,
            "mfa_method": "security-key",
            "security_keys": 2,
            "recovery_phone": False,
            "status": "active",
            "last_reviewed_on": None,
            "notes": None,
            "expected_version": box["version"],
        },
    )
    assert patch.status_code == 200, patch.text
    assert patch.json()["recovery_mailbox_id"] is None
    assert patch.json()["notes"] is None
    listed = client.get("/v1/mailboxes?limit=1000&order=asc&after_id=0", headers=owner)
    assert listed.status_code == 200
    assert "items" in listed.json()
