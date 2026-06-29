#!/usr/bin/env python3
"""Create controlled credit union self-healing test scenarios.

The script is dry-run by default. Salesforce actions require --apply. Repo
mutations are marker-based and reversible with --revert.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Any
from urllib.parse import quote, urlparse

ROOT = Path(__file__).resolve().parents[3]
PIPELINE_DIR = ROOT / "pipelines" / "credit_union_dwh"
CONTEXT_DIR = ROOT / ".context" / "self-healing-scenarios"
BRONZE_OPPORTUNITIES = PIPELINE_DIR / "assets" / "bronze" / "salesforce_opportunities.asset.yml"
SILVER_OPPORTUNITY_PIPELINE = PIPELINE_DIR / "assets" / "silver" / "salesforce_opportunity_pipeline.sql"
GOLD_PIPELINE_KPIS = PIPELINE_DIR / "assets" / "gold" / "pipeline_kpis.sql"

SCORE_BRONZE_BLOCK = """  # SELF_HEALING_SCENARIO_SCORE_FORMAT_START
  - name: credit_union_agent_test_score__c
    type: INTEGER
    description: Self-healing scenario field. Intentionally typed as INTEGER for the score-format drift test.
  # SELF_HEALING_SCENARIO_SCORE_FORMAT_END
"""

SCORE_SILVER_COLUMN_BLOCK = """  # SELF_HEALING_SCENARIO_SCORE_FORMAT_COLUMN_START
  - name: agent_test_score
    type: INTEGER
    description: Self-healing scenario score. Intentionally typed as INTEGER for the score-format drift test.
    update_on_merge: true
  # SELF_HEALING_SCENARIO_SCORE_FORMAT_COLUMN_END
"""

SCORE_OPPORTUNITIES_SELECT_BLOCK = """        -- SELF_HEALING_SCENARIO_SCORE_FORMAT_CAST_START
        o.credit_union_agent_test_score__c::INTEGER AS agent_test_score,
        -- SELF_HEALING_SCENARIO_SCORE_FORMAT_CAST_END
"""

SCORE_FINAL_SELECT_BLOCK = """    -- SELF_HEALING_SCENARIO_SCORE_FORMAT_OUTPUT_START
    o.agent_test_score,
    -- SELF_HEALING_SCENARIO_SCORE_FORMAT_OUTPUT_END
"""

GOOD_METRIC_LABEL = "'Opportunities with activity'"
BAD_METRIC_LABEL = "'Average approved loan APR'"
FIELD_WAIT_SECONDS = 90
FIELD_WAIT_INTERVAL_SECONDS = 5


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _write(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")


def _state(name: str, payload: dict[str, Any]) -> None:
    CONTEXT_DIR.mkdir(parents=True, exist_ok=True)
    (CONTEXT_DIR / f"{name}.json").write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def _ensure_contains(text: str, needle: str, path: Path) -> None:
    if needle not in text:
        raise RuntimeError(f"Expected marker text not found in {path}: {needle}")


def _safe_field_suffix(suffix: str | None) -> str:
    if not suffix:
        return ""
    cleaned = re.sub(r"[^A-Za-z0-9_]", "_", suffix).strip("_")
    if not cleaned:
        raise ValueError("--field-suffix must contain at least one letter or number")
    return f"_{cleaned[:20]}"


def _tier_field(suffix: str | None = None) -> str:
    return f"Credit_Union_Agent_Test_Tier{_safe_field_suffix(suffix)}__c"


def _remove_marker_block(text: str, marker: str, comment: str) -> str:
    pattern = re.compile(
        rf"(?ms)^[ \t]*{re.escape(comment)} {marker}_START\n.*?^[ \t]*{re.escape(comment)} {marker}_END\n"
    )
    return pattern.sub("", text)


def apply_score_format_repo_issue(apply: bool) -> None:
    files = [BRONZE_OPPORTUNITIES, SILVER_OPPORTUNITY_PIPELINE]
    for path in files:
        if not path.exists():
            raise FileNotFoundError(path)

    bronze = _read(BRONZE_OPPORTUNITIES)
    silver = _read(SILVER_OPPORTUNITY_PIPELINE)

    changed = False
    if (
        "SELF_HEALING_SCENARIO_SCORE_FORMAT_START" not in bronze
        and "  - name: credit_union_agent_test_score__c\n" not in bronze
    ):
        _ensure_contains(bronze, "  - name: close_date\n", BRONZE_OPPORTUNITIES)
        bronze = bronze.replace("  - name: close_date\n", SCORE_BRONZE_BLOCK + "  - name: close_date\n", 1)
        changed = True

    if "SELF_HEALING_SCENARIO_SCORE_FORMAT_COLUMN_START" not in silver:
        silver, column_replacements = re.subn(
            r"(?ms)^  - name: agent_test_score\n.*?(?=^  - name: close_date\n)",
            SCORE_SILVER_COLUMN_BLOCK,
            silver,
            count=1,
        )
        if column_replacements == 0:
            _ensure_contains(silver, "  - name: close_date\n", SILVER_OPPORTUNITY_PIPELINE)
            silver = silver.replace("  - name: close_date\n", SCORE_SILVER_COLUMN_BLOCK + "  - name: close_date\n", 1)
        changed = True

    if "SELF_HEALING_SCENARIO_SCORE_FORMAT_CAST_START" not in silver:
        silver, cast_replacements = re.subn(
            r"(?m)^        .*credit_union_agent_test_score__c.* AS agent_test_score,\n",
            SCORE_OPPORTUNITIES_SELECT_BLOCK,
            silver,
            count=1,
        )
        if cast_replacements == 0:
            _ensure_contains(silver, "        COALESCE(o.probability::DOUBLE, 0) AS probability,\n", SILVER_OPPORTUNITY_PIPELINE)
            silver = silver.replace(
                "        COALESCE(o.probability::DOUBLE, 0) AS probability,\n",
                "        COALESCE(o.probability::DOUBLE, 0) AS probability,\n" + SCORE_OPPORTUNITIES_SELECT_BLOCK,
                1,
            )
        changed = True

    if "o.agent_test_score," not in silver:
        _ensure_contains(silver, "    o.probability AS probability_pct,\n", SILVER_OPPORTUNITY_PIPELINE)
        silver = silver.replace(
            "    o.probability AS probability_pct,\n",
            "    o.probability AS probability_pct,\n" + SCORE_FINAL_SELECT_BLOCK,
            1,
        )
        changed = True

    if apply:
        _write(BRONZE_OPPORTUNITIES, bronze)
        _write(SILVER_OPPORTUNITY_PIPELINE, silver)
        _state("score-format-repo-issue", {"applied": changed, "files": [str(path) for path in files]})
        print("applied score-format repo issue")
    else:
        print("dry-run: score-format repo issue would be applied")


def revert_score_format_repo_issue(apply: bool) -> None:
    bronze = _remove_marker_block(_read(BRONZE_OPPORTUNITIES), "SELF_HEALING_SCENARIO_SCORE_FORMAT", "#")
    silver = _read(SILVER_OPPORTUNITY_PIPELINE)
    silver = _remove_marker_block(silver, "SELF_HEALING_SCENARIO_SCORE_FORMAT", "#")
    silver = _remove_marker_block(silver, "SELF_HEALING_SCENARIO_SCORE_FORMAT_COLUMN", "#")
    silver = _remove_marker_block(silver, "SELF_HEALING_SCENARIO_SCORE_FORMAT", "--")
    silver = _remove_marker_block(silver, "SELF_HEALING_SCENARIO_SCORE_FORMAT_CAST", "--")
    silver = _remove_marker_block(silver, "SELF_HEALING_SCENARIO_SCORE_FORMAT_OUTPUT", "--")
    silver, _ = re.subn(
        r"(?ms)^  - name: close_date\n",
        "  - name: agent_test_score\n"
        "    type: VARCHAR\n"
        "    description: Self-healing scenario score from Salesforce, preserved as source text.\n"
        "    update_on_merge: true\n"
        "  - name: close_date\n",
        silver,
        count=1,
    )
    silver = silver.replace(
        "        COALESCE(o.probability::DOUBLE, 0) AS probability,\n",
        "        COALESCE(o.probability::DOUBLE, 0) AS probability,\n"
        "        TO_VARCHAR(o.credit_union_agent_test_score__c) AS agent_test_score,\n",
        1,
    )
    if "    o.agent_test_score,\n" not in silver:
        silver = silver.replace(
            "    o.probability AS probability_pct,\n",
            "    o.probability AS probability_pct,\n"
            "    o.agent_test_score,\n",
            1,
        )

    if apply:
        _write(BRONZE_OPPORTUNITIES, bronze)
        _write(SILVER_OPPORTUNITY_PIPELINE, silver)
        _state("score-format-repo-issue", {"reverted": True})
        print("reverted score-format repo issue")
    else:
        print("dry-run: score-format repo issue would be reverted")


def apply_metric_description_issue(apply: bool) -> None:
    text = _read(GOLD_PIPELINE_KPIS)
    if BAD_METRIC_LABEL in text:
        changed = False
    else:
        _ensure_contains(text, GOOD_METRIC_LABEL, GOLD_PIPELINE_KPIS)
        text = text.replace(GOOD_METRIC_LABEL, BAD_METRIC_LABEL, 1)
        changed = True

    if apply:
        _write(GOLD_PIPELINE_KPIS, text)
        _state("metric-description-repo-issue", {"applied": changed, "file": str(GOLD_PIPELINE_KPIS)})
        print("applied metric-description repo issue")
    else:
        print("dry-run: metric-description repo issue would be applied")


def revert_metric_description_issue(apply: bool) -> None:
    text = _read(GOLD_PIPELINE_KPIS).replace(BAD_METRIC_LABEL, GOOD_METRIC_LABEL)
    if apply:
        _write(GOLD_PIPELINE_KPIS, text)
        _state("metric-description-repo-issue", {"reverted": True})
        print("reverted metric-description repo issue")
    else:
        print("dry-run: metric-description repo issue would be reverted")


def _load_bruin_config() -> dict[str, Any]:
    raw = os.environ.get("SALESFORCE_CONNECTION")
    if raw:
        return {"connections": {"salesforce": [json.loads(raw)]}}

    try:
        import yaml  # type: ignore
    except ImportError as exc:
        raise RuntimeError("PyYAML is required to read .bruin.yml, or set SALESFORCE_CONNECTION JSON.") from exc

    path = ROOT / ".bruin.yml"
    if not path.exists():
        raise FileNotFoundError("Could not find .bruin.yml at repo root; set SALESFORCE_CONNECTION JSON instead.")
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def _salesforce_connection() -> dict[str, Any]:
    config = _load_bruin_config()
    default_env = config.get("default_environment", "default")
    roots = [
        config.get("connections", {}),
        config.get("environments", {}).get(default_env, {}).get("connections", {}),
        config.get("environments", {}).get("default", {}).get("connections", {}),
    ]
    for root in roots:
        candidates = root.get("salesforce") or []
        for conn in candidates:
            if conn.get("name") == "salesforce" or len(candidates) == 1:
                return conn
    raise RuntimeError("Salesforce connection named 'salesforce' was not found.")


def _salesforce_base_url(domain: str) -> str:
    domain = domain.rstrip("/")
    if domain.startswith(("http://", "https://")):
        return domain
    if domain.endswith(".salesforce.com"):
        return f"https://{domain}"
    return f"https://{domain}.salesforce.com"


def _connect_salesforce() -> Any:
    try:
        from simple_salesforce import Salesforce
    except ImportError as exc:
        raise RuntimeError("simple-salesforce is required. Install the bronze asset requirements first.") from exc

    conn = _salesforce_connection()
    domain = conn.get("domain") or "login"

    if conn.get("access_token"):
        return Salesforce(instance_url=_salesforce_base_url(domain), session_id=conn["access_token"])

    username = conn["username"]
    password = conn["password"]
    token = conn["token"]

    if isinstance(domain, str) and domain.startswith("http"):
        parsed = urlparse(domain)
        hostname = parsed.netloc
        candidates = [hostname]
        if hostname.endswith(".my.salesforce.com"):
            candidates.append(hostname[: -len(".my.salesforce.com")])
        if hostname.endswith(".salesforce.com"):
            candidates.append(hostname[: -len(".salesforce.com")])
        candidates.extend(["login", "test"])
    else:
        candidates = [domain, "login", "test"]

    last_error: Exception | None = None
    for candidate in dict.fromkeys(candidates):
        try:
            return Salesforce(username=username, password=password, security_token=token, domain=candidate)
        except Exception as exc:
            last_error = exc
    raise last_error or RuntimeError("Salesforce login failed")


def _tooling_query(sf: Any, soql: str) -> dict[str, Any]:
    return sf.toolingexecute(f"query/?q={quote(soql)}")


def _field_record(sf: Any, developer_name: str) -> dict[str, Any] | None:
    result = _tooling_query(
        sf,
        "SELECT Id, DeveloperName FROM CustomField "
        f"WHERE TableEnumOrId = 'Opportunity' AND DeveloperName = '{developer_name}' LIMIT 1",
    )
    records = result.get("records") or []
    return records[0] if records else None


def _field_exists(sf: Any, developer_name: str) -> bool:
    return _field_record(sf, developer_name) is not None


def _current_profile_permission_set_id(sf: Any) -> str | None:
    username = _salesforce_connection().get("username")
    if not username:
        return None

    escaped_username = username.replace("\\", "\\\\").replace("'", "\\'")
    user_records = sf.query(
        "SELECT Id, ProfileId FROM User "
        f"WHERE Username = '{escaped_username}' "
        "LIMIT 1"
    ).get("records", [])
    if not user_records:
        return None

    permission_sets = sf.query(
        "SELECT Id FROM PermissionSet "
        f"WHERE ProfileId = '{user_records[0]['ProfileId']}' "
        "AND IsOwnedByProfile = true "
        "LIMIT 1"
    ).get("records", [])
    return permission_sets[0]["Id"] if permission_sets else None


def _grant_current_profile_field_access(sf: Any, full_name: str, apply: bool) -> None:
    parent_id = _current_profile_permission_set_id(sf)
    if not parent_id:
        print(f"could not resolve current profile permission set; skipping FLS grant for {full_name}")
        return

    existing = sf.query(
        "SELECT Id, PermissionsRead, PermissionsEdit FROM FieldPermissions "
        f"WHERE ParentId = '{parent_id}' "
        f"AND Field = '{full_name}' "
        "LIMIT 1"
    ).get("records", [])

    if not apply:
        action = "update" if existing else "create"
        print(f"dry-run: would {action} FieldPermissions for {full_name}")
        return

    payload = {
        "ParentId": parent_id,
        "SobjectType": full_name.split(".", 1)[0],
        "Field": full_name,
        "PermissionsRead": True,
        "PermissionsEdit": True,
    }
    if existing:
        sf.FieldPermissions.update(
            existing[0]["Id"],
            {"PermissionsRead": True, "PermissionsEdit": True},
        )
        print(f"updated FieldPermissions for {full_name}")
    else:
        sf.FieldPermissions.create(payload)
        print(f"created FieldPermissions for {full_name}")


def _ensure_custom_field(sf: Any, full_name: str, metadata: dict[str, Any], apply: bool) -> None:
    developer_name = full_name.split(".", 1)[1].replace("__c", "")
    if _field_exists(sf, developer_name):
        print(f"Salesforce field exists: {full_name}")
        _grant_current_profile_field_access(sf, full_name, apply)
        return

    if not apply:
        print(f"dry-run: Salesforce field would be created: {full_name}")
        _grant_current_profile_field_access(sf, full_name, apply)
        return

    payload = {"FullName": full_name, "Metadata": metadata}
    result = sf.toolingexecute("sobjects/CustomField", method="POST", data=payload)
    if not result.get("success"):
        raise RuntimeError(f"Salesforce CustomField create failed for {full_name}: {result}")
    print(f"created Salesforce field: {full_name}")
    _grant_current_profile_field_access(sf, full_name, apply)


def _field_visible_to_rest(sf: Any, field: str) -> bool:
    try:
        fields = getattr(sf, "Opportunity").describe().get("fields", [])
    except Exception:
        return False
    return any(item.get("name") == field for item in fields)


def _wait_for_field_visible_to_rest(sf: Any, field: str, apply: bool) -> bool:
    if not apply:
        return True

    deadline = time.monotonic() + FIELD_WAIT_SECONDS
    while time.monotonic() <= deadline:
        if _field_visible_to_rest(sf, field):
            return True
        time.sleep(FIELD_WAIT_INTERVAL_SECONDS)

    return False


def _demo_opportunity_ids(sf: Any, limit: int, field: str | None = None, non_null_only: bool = False) -> list[str]:
    where = "Name LIKE 'Credit Union Demo%'"
    if field and non_null_only:
        where += f" AND {field} != null"
    limit_clause = f"LIMIT {int(limit)}" if limit > 0 else ""
    result = sf.query_all(
        "SELECT Id, Name FROM Opportunity "
        f"WHERE {where} "
        "ORDER BY LastModifiedDate DESC "
        f"{limit_clause}"
    )
    return [row["Id"] for row in result.get("records", [])]


def _populate_opportunity_field(sf: Any, field: str, values: list[str], limit: int, apply: bool) -> None:
    if not _wait_for_field_visible_to_rest(sf, field, apply):
        raise RuntimeError(
            f"Salesforce field Opportunity.{field} was created but is not visible to REST/describe yet. "
            "Wait for Salesforce metadata propagation, then rerun this scenario."
        )

    ids = _demo_opportunity_ids(sf, limit)
    if not ids:
        raise RuntimeError("No Credit Union Demo opportunities found. Run the seed asset first.")
    if not apply:
        print(f"dry-run: would update {len(ids)} Opportunity rows field {field}")
        return

    for idx, opportunity_id in enumerate(ids):
        sf.Opportunity.update(opportunity_id, {field: values[idx % len(values)]})
    print(f"updated {len(ids)} Opportunity rows field {field}")


def _clear_opportunity_field(sf: Any, field: str, limit: int, apply: bool) -> None:
    developer_name = field.replace("__c", "")
    if not _field_exists(sf, developer_name):
        print(f"Salesforce field already absent: Opportunity.{field}; no Opportunity values to clear")
        return
    if not _field_visible_to_rest(sf, field):
        print(f"Salesforce field Opportunity.{field} is not visible to REST/describe; skipping value clear")
        return

    ids = _demo_opportunity_ids(sf, limit, field=field, non_null_only=True)
    if not ids:
        print(f"no Credit Union Demo Opportunity rows currently have {field} populated")
        return
    if not apply:
        print(f"dry-run: would clear {field} on {len(ids)} Opportunity rows")
        return

    for opportunity_id in ids:
        sf.Opportunity.update(opportunity_id, {field: None})
    print(f"cleared {field} on {len(ids)} Opportunity rows")


def _delete_custom_field(sf: Any, full_name: str, apply: bool) -> None:
    developer_name = full_name.split(".", 1)[1].replace("__c", "")
    record = _field_record(sf, developer_name)
    if not record:
        print(f"Salesforce field already absent: {full_name}")
        return
    if not apply:
        print(f"dry-run: would delete Salesforce field {full_name}")
        return

    try:
        sf.toolingexecute(f"sobjects/CustomField/{record['Id']}", method="DELETE")
        print(f"deleted Salesforce field: {full_name}")
    except Exception as exc:
        print(f"could not delete Salesforce field {full_name}: {exc}")
        print("values were cleared when possible; use --field-suffix for a fresh additive-field repeat demo")


def apply_salesforce_new_attribute(apply: bool, limit: int, field_suffix: str | None = None) -> None:
    sf = _connect_salesforce()
    field = _tier_field(field_suffix)
    _ensure_custom_field(
        sf,
        f"Opportunity.{field}",
        {"type": "Text", "label": "credit union Agent Test Tier", "length": 40, "required": False},
        apply,
    )
    _populate_opportunity_field(
        sf,
        field,
        ["Branch Priority", "Member Growth", "Cross Sell", "Digital Follow-up"],
        limit,
        apply,
    )
    _state("salesforce-new-attribute", {"field": field, "limit": limit, "applied": apply})


def revert_salesforce_new_attribute(
    apply: bool,
    limit: int,
    delete_field: bool,
    field_suffix: str | None = None,
) -> None:
    sf = _connect_salesforce()
    field = _tier_field(field_suffix)
    _clear_opportunity_field(sf, field, limit, apply)
    if delete_field:
        _delete_custom_field(sf, f"Opportunity.{field}", apply)
    _state(
        "salesforce-new-attribute",
        {"field": field, "limit": limit, "reverted": apply, "delete_field": delete_field},
    )


def apply_salesforce_score_format(apply: bool, limit: int) -> None:
    sf = _connect_salesforce()
    field = "Credit_Union_Agent_Test_Score__c"
    _ensure_custom_field(
        sf,
        f"Opportunity.{field}",
        {"type": "Text", "label": "credit union Agent Test Score", "length": 40, "required": False},
        apply,
    )
    _populate_opportunity_field(sf, field, [f"SCORE-{100 + idx}" for idx in range(10)], limit, apply)
    _state("salesforce-score-format", {"field": field, "limit": limit, "applied": apply})


def revert_salesforce_score_format(apply: bool, limit: int, delete_field: bool) -> None:
    sf = _connect_salesforce()
    field = "Credit_Union_Agent_Test_Score__c"
    _clear_opportunity_field(sf, field, limit, apply)
    if delete_field:
        _delete_custom_field(sf, f"Opportunity.{field}", apply)
    _state(
        "salesforce-score-format",
        {"field": field, "limit": limit, "reverted": apply, "delete_field": delete_field},
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="target", required=True)

    salesforce = subparsers.add_parser("salesforce", help="Create Salesforce source-data scenarios.")
    salesforce.add_argument("scenario", choices=["new-attribute", "score-format"])
    salesforce.add_argument(
        "--limit",
        type=int,
        default=25,
        help="Number of Credit Union Demo opportunities to update or clear. Use 0 to clear all matching demo rows.",
    )
    salesforce.add_argument("--apply", action="store_true", help="Actually mutate Salesforce.")
    salesforce.add_argument("--revert", action="store_true", help="Undo the Salesforce scenario mutation.")
    salesforce.add_argument(
        "--delete-field",
        action="store_true",
        help="With --revert, delete the scenario custom field after clearing values.",
    )
    salesforce.add_argument(
        "--field-suffix",
        help="Optional suffix for the new-attribute custom field, useful when Salesforce blocks hard deletion.",
    )

    repo = subparsers.add_parser("repo", help="Create or revert local repo scenarios.")
    repo.add_argument("scenario", choices=["score-format", "metric-description"])
    action = repo.add_mutually_exclusive_group()
    action.add_argument("--apply", action="store_true", help="Apply the repo mutation.")
    action.add_argument("--revert", action="store_true", help="Revert the repo mutation.")

    args = parser.parse_args()

    if args.target == "salesforce":
        if args.scenario == "new-attribute":
            if args.revert:
                revert_salesforce_new_attribute(args.apply, args.limit, args.delete_field, args.field_suffix)
            else:
                apply_salesforce_new_attribute(args.apply, args.limit, args.field_suffix)
        elif args.scenario == "score-format":
            if args.revert:
                revert_salesforce_score_format(args.apply, args.limit, args.delete_field)
            else:
                apply_salesforce_score_format(args.apply, args.limit)
        return

    if args.target == "repo":
        if args.scenario == "score-format":
            if args.revert:
                revert_score_format_repo_issue(True)
            else:
                apply_score_format_repo_issue(args.apply)
        elif args.scenario == "metric-description":
            if args.revert:
                revert_metric_description_issue(True)
            else:
                apply_metric_description_issue(args.apply)


if __name__ == "__main__":
    main()
