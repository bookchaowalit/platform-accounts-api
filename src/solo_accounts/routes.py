"""``GET /v1/risk-report``: what in the inventory makes an account easier to lose or to link.

The report reads every identity, domain, mailbox and account in the caller's
workspace (read permission on all four is required) and returns findings with a
severity, a stable code and the record they are about. It never returns email
addresses: mailboxes are named by their ``address_hint``.
"""

from datetime import date, timedelta
from typing import Annotated, Any, get_args

from fastapi import HTTPException

from cellkit.app import Context
from cellkit.auth import Principal

Row = dict[str, Any]  # one database row (psycopg dict_row) or one finding

SEVERITY_ORDER = {"high": 0, "medium": 1, "low": 2, "info": 3}
WEAK_MFA = {"sms": "high", "none": "high", "unknown": "medium"}
LIVE_MAILBOX = {"active", "unverified", "dormant"}
LIVE_ACCOUNT = {"setup", "active", "paused"}
# A mailbox that can reset this many others is a single point of failure.
RECOVERY_HUB = 3
REVIEW_DAYS = 180
RENEWAL_WARNING_DAYS = 45
# Per resource; a bigger workspace gets 413 instead of an unbounded scan.
MAX_ROWS = 20_000
MAX_FINDINGS = 1_000  # counts always cover everything; the list is cut after this many
COLUMNS = {
    "identity": "id, slug, trust_zone, isolation_group, relation",
    "domain": "id, name, status, auto_renew, renews_on",
    "mailbox": (
        "id, identity_id, domain_id, recovery_mailbox_id, security_keys, mfa_method, status,"
        " last_reviewed_on, kind, address_hint"
    ),
    "account": (
        "id, identity_id, login_mailbox_id, admin_account_id, mfa_primary, status, social_login,"
        " phone_bound, platform, handle, kind"
    ),
}


def finding(
    severity: str,
    code: str,
    kind: str,
    record: Row,
    label: str,
    message: str,
) -> Row:
    return {
        "severity": severity,
        "code": code,
        "subject": {"type": kind, "id": record["id"], "label": label},
        "message": message,
    }


def analyse(
    identities: list[Row],
    domains: list[Row],
    mailboxes: list[Row],
    accounts: list[Row],
    today: date | None = None,
) -> list[Row]:
    today = today or date.today()
    ident = {row["id"]: row for row in identities}
    dom = {row["id"]: row for row in domains}  # noqa: F841 - unused, but building it raises KeyError on a domain row without an id; removing it changes behaviour
    mbox = {row["id"]: row for row in mailboxes}
    acct = {row["id"]: row for row in accounts}
    out: list[Row] = []

    def m_label(row: Row) -> str:
        hint: str = row["address_hint"]  # required text column
        return hint

    def a_label(row: Row) -> str:
        return f"{row['platform']}:{row.get('handle') or row['id']}"

    def zone(identity_id: int | None) -> str | None:
        return ident.get(identity_id, {}).get("trust_zone")

    def group(identity_id: int | None) -> str | None:
        row = ident.get(identity_id, {})
        return row.get("isolation_group") or row.get("slug")

    live_mail = [row for row in mailboxes if row["status"] in LIVE_MAILBOX]
    live_acct = [row for row in accounts if row["status"] in LIVE_ACCOUNT]

    # Recovery hubs: one mailbox that can reset many others.
    dependants: dict[int, list[Row]] = {}
    for row in live_mail:
        if row.get("recovery_mailbox_id"):
            dependants.setdefault(row["recovery_mailbox_id"], []).append(row)
    for hub_id, rows in dependants.items():
        hub = mbox.get(hub_id)
        if hub is None or len(rows) < RECOVERY_HUB:
            continue
        if hub["security_keys"] >= 2:
            out.append(
                finding(
                    "info",
                    "recovery_hub",
                    "mailbox",
                    hub,
                    m_label(hub),
                    f"Recovers {len(rows)} mailboxes and has {hub['security_keys']} security keys.",
                )
            )
        else:
            out.append(
                finding(
                    "high",
                    "recovery_hub_unprotected",
                    "mailbox",
                    hub,
                    m_label(hub),
                    f"Recovers {len(rows)} mailboxes but has fewer than 2 security keys; "
                    "losing it loses all of them.",
                )
            )

    # Recovery that points at itself or loops.
    for row in live_mail:
        seen = {row["id"]}
        nxt = row.get("recovery_mailbox_id")
        while nxt is not None:
            if nxt in seen:
                out.append(
                    finding(
                        "high",
                        "recovery_cycle",
                        "mailbox",
                        row,
                        m_label(row),
                        "Its recovery chain comes back to itself; there is no independent way back in.",
                    )
                )
                break
            seen.add(nxt)
            nxt = mbox.get(nxt, {}).get("recovery_mailbox_id")
        recovery = mbox.get(row.get("recovery_mailbox_id"))
        if recovery is not None and recovery["status"] in {
            "dormant",
            "to-delete",
            "deleted",
        }:
            out.append(
                finding(
                    "high" if recovery["status"] == "deleted" else "medium",
                    "recovery_not_live",
                    "mailbox",
                    row,
                    m_label(row),
                    f"Its recovery mailbox {m_label(recovery)} is {recovery['status']}.",
                )
            )
        if (
            recovery is not None
            and ident.get(row["identity_id"], {}).get("relation") == "self"
            and ident.get(recovery["identity_id"], {}).get("relation") == "work"
        ):
            out.append(
                finding(
                    "medium",
                    "recovery_via_work",
                    "mailbox",
                    row,
                    m_label(row),
                    "Recovers through a work mailbox you lose when you leave.",
                )
            )

    # Weak MFA on what is still in use.
    out.extend(
        finding(
            WEAK_MFA[row["mfa_method"]],
            "weak_mfa",
            "mailbox",
            row,
            m_label(row),
            f"Second factor is {row['mfa_method']}; use a passkey or security key.",
        )
        for row in live_mail
        if row["kind"] == "mailbox" and row["mfa_method"] in WEAK_MFA
    )
    out.extend(
        finding(
            WEAK_MFA[row["mfa_primary"]],
            "weak_mfa",
            "account",
            row,
            a_label(row),
            f"Second factor is {row['mfa_primary']}.",
        )
        for row in live_acct
        if row["mfa_primary"] in WEAK_MFA
        and row["kind"] in {"profile", "service", "business"}
    )

    # Trust-zone crossings that tie a separated brand to the owner.
    for row in live_acct:
        own_zone, own_group = zone(row["identity_id"]), group(row["identity_id"])
        login = mbox.get(row.get("login_mailbox_id"))
        if (
            own_zone == "z2-separated"
            and login is not None
            and group(login["identity_id"]) != own_group
        ):
            out.append(
                finding(
                    "high",
                    "zone_crossing_login",
                    "account",
                    row,
                    a_label(row),
                    "A separated brand signs in with a mailbox from another identity group.",
                )
            )
        admin = acct.get(row.get("admin_account_id"))
        if (
            own_zone == "z2-separated"
            and admin is not None
            and group(admin["identity_id"]) != own_group
        ):
            out.append(
                finding(
                    "medium",
                    "zone_crossing_admin",
                    "account",
                    row,
                    a_label(row),
                    f"Administered by {a_label(admin)} from another identity group; "
                    "the platform links them.",
                )
            )
        if own_zone == "z2-separated" and row["social_login"] != "none":
            out.append(
                finding(
                    "medium",
                    "social_login_separated",
                    "account",
                    row,
                    a_label(row),
                    f"Signs in with {row['social_login']}, which ties it to that account.",
                )
            )
        if own_zone == "z2-separated" and row["phone_bound"]:
            out.append(
                finding(
                    "low",
                    "phone_bound_separated",
                    "account",
                    row,
                    a_label(row),
                    "A phone number on a separated brand lets the platform link it to you.",
                )
            )
        if login is not None and login["status"] in {"to-delete", "deleted"}:
            out.append(
                finding(
                    "high",
                    "login_mailbox_not_live",
                    "account",
                    row,
                    a_label(row),
                    f"Signs in with {m_label(login)}, which is {login['status']}; move it first.",
                )
            )

    # Domains that are being let go while mail still depends on them.
    for row in domains:
        # A mailbox marked to-delete still receives password resets until it is really gone.
        users = [
            m
            for m in mailboxes
            if m.get("domain_id") == row["id"] and m["status"] != "deleted"
        ]
        logins = [
            a
            for a in live_acct
            if mbox.get(a.get("login_mailbox_id"), {}).get("domain_id") == row["id"]
        ]
        letting_go = row["status"] in {"releasing", "released"} or not row["auto_renew"]
        if letting_go and (users or logins):
            out.append(
                finding(
                    "high",
                    "domain_release_takeover",
                    "domain",
                    row,
                    row["name"],
                    f"Not renewing, but {len(users)} mailbox(es) and {len(logins)} account login(s) "
                    "still use it; whoever buys it can reset them.",
                )
            )
        renews = row.get("renews_on")
        if (
            renews
            and not row["auto_renew"]
            and row["status"] == "active"
            and renews <= today + timedelta(days=RENEWAL_WARNING_DAYS)
        ):
            out.append(
                finding(
                    "medium",
                    "domain_expiring",
                    "domain",
                    row,
                    row["name"],
                    f"Expires on {renews.isoformat()} with auto-renew off.",
                )
            )

    # Mailboxes nobody has looked at in a while.
    for row in live_mail:
        reviewed = row.get("last_reviewed_on")
        if row["kind"] == "mailbox" and (
            reviewed is None or reviewed < today - timedelta(days=REVIEW_DAYS)
        ):
            out.append(
                finding(
                    "low",
                    "review_overdue",
                    "mailbox",
                    row,
                    m_label(row),
                    "Not reviewed in the last 180 days.",
                )
            )

    out.sort(
        key=lambda f: (
            SEVERITY_ORDER[f["severity"]],
            f["code"],
            f["subject"]["type"],
            f["subject"]["id"],
        )
    )
    return out


def register(ctx: Context) -> None:
    schema = ctx.cell.schema
    names = ("identity", "domain", "mailbox", "account")

    # ctx.caller is Annotated[Principal, Depends(...)]. Restating it with its dependency keeps a real
    # annotation object (FastAPI must see the dependency, not a string) that mypy reads as Principal.
    authenticated = get_args(ctx.caller)[1]

    @ctx.app.get("/v1/risk-report", tags=["risk"])
    def risk_report(caller: Annotated[Principal, authenticated]) -> dict[str, Any]:
        for name in names:
            ctx.allow(caller, f"{ctx.cell.name}.{name}:read", name)
        rows: dict[str, list[Row]] = {}
        with ctx.bound(caller) as conn:
            for name in names:
                table = ctx.cell.resource(name).table
                rows[name] = conn.execute(
                    f"SELECT {COLUMNS[name]} FROM {schema}.{table} ORDER BY id LIMIT %s",
                    (MAX_ROWS + 1,),
                ).fetchall()
                if len(rows[name]) > MAX_ROWS:
                    raise HTTPException(
                        status_code=413,
                        detail={
                            "error": "workspace_too_large",
                            "resource": name,
                            "limit": MAX_ROWS,
                        },
                    )
        findings = analyse(
            rows["identity"], rows["domain"], rows["mailbox"], rows["account"]
        )
        counts = {
            level: sum(1 for f in findings if f["severity"] == level)
            for level in SEVERITY_ORDER
        }
        return {
            "generated_on": date.today().isoformat(),
            "counts": counts,
            "findings": findings[:MAX_FINDINGS],
            "truncated": len(findings) > MAX_FINDINGS,
            "totals": {name: len(rows[name]) for name in names},
        }
