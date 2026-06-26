"""Helpers for Bruin Python assets that mutate Salesforce.

Copy or import this helper from a Bruin Python asset that declares:

secrets:
  - key: salesforce
    inject_as: SALESFORCE_CONNECTION
"""

from __future__ import annotations

import json
import logging
import os
from collections.abc import Iterable, Iterator, Sequence
from typing import Any, TypeVar
from urllib.parse import urlparse

import requests
from simple_salesforce import Salesforce

LOGGER = logging.getLogger(__name__)
T = TypeVar("T")


def salesforce_from_env(env_var: str = "SALESFORCE_CONNECTION") -> Salesforce:
    """Build a Salesforce client from a Bruin-injected connection JSON string."""

    raw = os.environ[env_var]
    conn = json.loads(raw)
    domain = conn.get("domain") or "login"

    if conn.get("access_token"):
        return Salesforce(
            instance_url=salesforce_base_url(domain),
            session_id=conn["access_token"],
        )

    if conn.get("client_id") and conn.get("client_secret"):
        response = requests.post(
            f"{salesforce_base_url(domain)}/services/oauth2/token",
            data={
                "grant_type": conn.get("grant_type", "client_credentials"),
                "client_id": conn["client_id"],
                "client_secret": conn["client_secret"],
            },
            timeout=30,
        )
        response.raise_for_status()
        payload = response.json()
        return Salesforce(
            instance_url=payload["instance_url"],
            session_id=payload["access_token"],
        )

    username = conn["username"]
    password = conn["password"]
    token = conn["token"]
    last_error: Exception | None = None

    for candidate in domain_candidates(domain):
        try:
            return Salesforce(
                username=username,
                password=password,
                security_token=token,
                domain=candidate,
            )
        except Exception as exc:  # simple_salesforce raises several auth types.
            last_error = exc
            LOGGER.debug("Salesforce login failed for configured domain candidate %s", candidate)

    raise last_error or RuntimeError("Salesforce login failed")


def salesforce_base_url(domain: str) -> str:
    domain = domain.rstrip("/")
    if domain.startswith(("http://", "https://")):
        return domain
    if domain.endswith(".salesforce.com"):
        return f"https://{domain}"
    return f"https://{domain}.salesforce.com"


def domain_candidates(domain: str) -> list[str]:
    if domain.startswith(("http://", "https://")):
        hostname = urlparse(domain).netloc
        candidates = [hostname]
        if hostname.endswith(".my.salesforce.com"):
            candidates.append(hostname[: -len(".my.salesforce.com")])
        elif hostname.endswith(".salesforce.com"):
            candidates.append(hostname[: -len(".salesforce.com")])
        candidates.extend(["login", "test"])
    else:
        candidates = [domain, "login", "test"]
    return list(dict.fromkeys(candidates))


def chunks(items: Sequence[T], size: int = 200) -> Iterator[Sequence[T]]:
    for index in range(0, len(items), size):
        yield items[index : index + size]


def soql_literal(value: Any) -> str:
    if value is None:
        return "NULL"
    text = str(value).replace("\\", "\\\\").replace("'", "\\'")
    return f"'{text}'"


def query_existing_by_field(
    sf: Salesforce,
    object_name: str,
    match_field: str,
    values: Iterable[Any],
    select_fields: Sequence[str] | None = None,
    batch_size: int = 200,
) -> dict[str, dict[str, Any]]:
    """Return existing Salesforce records keyed by the requested match field."""

    unique_values = [value for value in dict.fromkeys(values) if value not in (None, "")]
    fields = list(dict.fromkeys(["Id", match_field, *(select_fields or [])]))
    existing: dict[str, dict[str, Any]] = {}

    for batch in chunks(unique_values, batch_size):
        literals = ", ".join(soql_literal(value) for value in batch)
        soql = f"SELECT {', '.join(fields)} FROM {object_name} WHERE {match_field} IN ({literals})"
        for record in sf.query_all(soql)["records"]:
            record.pop("attributes", None)
            existing[str(record[match_field])] = record

    return existing


def create_update_by_match_field(
    sf: Salesforce,
    object_name: str,
    records: Sequence[dict[str, Any]],
    match_field: str,
    dry_run: bool = True,
) -> dict[str, Any]:
    """Create or update records by Salesforce Id or a pre-queried natural key."""

    if not records:
        return {"created": 0, "updated": 0, "skipped": 0, "failed": 0, "errors": []}

    existing = query_existing_by_field(
        sf,
        object_name,
        match_field,
        [record.get(match_field) for record in records],
    )
    object_api = getattr(sf, object_name)
    summary: dict[str, Any] = {"created": 0, "updated": 0, "skipped": 0, "failed": 0, "errors": []}

    for record in records:
        key = record.get(match_field)
        if key in (None, ""):
            summary["skipped"] += 1
            summary["errors"].append({"key": key, "error": f"missing {match_field}"})
            continue

        payload = dict(record)
        current = existing.get(str(key))
        try:
            if dry_run:
                if current:
                    summary["updated"] += 1
                elif match_field == "Id":
                    summary["skipped"] += 1
                    summary["errors"].append({"key": key, "error": "Id not found"})
                else:
                    summary["created"] += 1
            elif current:
                payload.pop("Id", None)
                object_api.update(current["Id"], payload)
                summary["updated"] += 1
            elif match_field == "Id":
                summary["skipped"] += 1
                summary["errors"].append({"key": key, "error": "Id not found"})
            else:
                object_api.create(payload)
                summary["created"] += 1
        except Exception as exc:
            summary["failed"] += 1
            summary["errors"].append({"key": key, "error": str(exc)})

    return summary
