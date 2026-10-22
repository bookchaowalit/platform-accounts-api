"""Platform accounts: one record per platform handle, planned until set up, no secrets stored."""

from inventory_helpers import account, identity, mailbox


def test_a_new_account_is_planned_with_unknown_mfa(client, owner):
    owner_identity = identity(client, owner).json()["id"]
    created = account(client, owner, owner_identity)
    assert created.status_code == 201, created.text
    row = created.json()
    assert row["status"] == "planned"
    assert row["kind"] == "profile"
    assert row["mfa_primary"] == "unknown"
    assert row["mfa_backup"] == "unknown"
    assert row["social_login"] == "none"
    assert row["phone_bound"] is False


def test_a_handle_is_used_once_per_platform(client, owner):
    owner_identity = identity(client, owner).json()["id"]
    assert (
        account(client, owner, owner_identity, platform="x", handle="book").status_code
        == 201
    )
    again = account(client, owner, owner_identity, platform="x", handle="book")
    assert again.status_code == 409
    other_platform = account(
        client, owner, owner_identity, platform="youtube", handle="book"
    )
    assert other_platform.status_code == 201


def test_social_login_is_one_of_the_known_providers(client, owner):
    owner_identity = identity(client, owner).json()["id"]
    assert (
        account(client, owner, owner_identity, social_login="github").status_code == 422
    )
    assert (
        account(client, owner, owner_identity, social_login="google").status_code == 201
    )


def test_offline_codes_are_a_backup_factor_only(client, owner):
    owner_identity = identity(client, owner).json()["id"]
    as_primary = account(client, owner, owner_identity, mfa_primary="offline-codes")
    assert as_primary.status_code == 422
    as_backup = account(client, owner, owner_identity, mfa_backup="offline-codes")
    assert as_backup.status_code == 201


def test_an_account_links_its_login_mailbox_and_admin_account(client, owner):
    owner_identity = identity(client, owner).json()["id"]
    login = mailbox(client, owner, owner_identity).json()["id"]
    admin = account(client, owner, owner_identity, kind="business").json()["id"]
    page = account(
        client,
        owner,
        owner_identity,
        kind="page",
        login_mailbox_id=login,
        admin_account_id=admin,
    )
    assert page.status_code == 201, page.text
    assert page.json()["login_mailbox_id"] == login
    assert page.json()["admin_account_id"] == admin


def test_an_unknown_login_mailbox_is_refused(client, owner):
    owner_identity = identity(client, owner).json()["id"]
    response = account(client, owner, owner_identity, login_mailbox_id=999_999_999)
    assert response.status_code == 422
    assert response.json()["detail"] == {"error": "reference_not_found"}
