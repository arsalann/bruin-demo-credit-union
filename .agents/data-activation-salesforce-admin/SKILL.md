---
name: data-activation-salesforce-admin
description: Activate warehouse or user-provided data into Salesforce and perform Salesforce admin changes from a Bruin Slack agent. Use when a user asks to create, update, upsert, disable, assign, enrich, sync, backfill, or otherwise change Salesforce records, CRM campaigns, leads, contacts, accounts, opportunities, tasks, events, products, price books, users, permissions, fields, layouts, metadata, or Salesforce operational settings using Bruin connections, Bruin assets, or Bruin Cloud context.
---

# Data Activation Salesforce Admin

## Core Rules

Use this skill to turn Slack requests into verified Salesforce mutations. Prefer Bruin assets and Bruin CLI for repeatable work; use one-off scripts only for narrow, auditable admin actions.

- Read the local project instructions first: `AGENTS.md`, client `PLAN.md`/`handoff.md` or `HANDOFF.md`, and the active pipeline `README.md`.
- Use Bruin MCP documentation for Bruin-specific guidance, then Bruin CLI for validation, lineage, runs, and warehouse queries.
- Never print, paste, log, or write Salesforce tokens, passwords, security tokens, private keys, or `.bruin.yml` contents into tracked files.
- Use the existing Bruin Salesforce connection named `salesforce` unless the user explicitly chooses another connection.
- Treat every Salesforce write as production-impacting until the target org and environment are proven otherwise.
- For destructive, broad, security-sensitive, or admin metadata changes, require explicit approval after a dry-run summary.

## Workflow

### 1. Scope the Slack request

Extract and confirm:

- Salesforce org/environment.
- Object API names and field API names.
- Operation: create, update, upsert, delete/deactivate, ownership change, metadata/admin change.
- Record selection source: warehouse query, Bruin asset output, CSV, Slack-provided IDs, or Salesforce SOQL.
- Match key: Salesforce `Id`, an external ID field, or a stable natural key.
- Expected row count and success criteria.

Ask one concise clarifying question only when a write cannot be safely scoped. Do not guess object names, field names, orgs, or match keys.

### 2. Inspect context and connections

Use these checks before building or running a mutation:

```bash
bruin connections list
bruin validate --fast <pipeline-or-asset-path>
bruin lineage <asset-path>
```

For warehouse-sourced activations, inspect candidate records with `bruin query` and include a reason:

```bash
bruin query --description "Preview Salesforce activation candidates before updating Contact opt-in fields" "<SQL>"
```

Salesforce `bruin connections test --name salesforce` may not be supported for every connector path. If needed, validate by running a narrow dry-run Bruin Python asset that injects the `salesforce` connection and executes a harmless SOQL probe.

### 3. Use Bruin-injected Salesforce credentials

For Python activation assets, use the same connection shape as `pipelines/credit_union_dwh/assets/bronze/seed_salesforce_demo_data.py`:

```python
"""@bruin
name: ops.activate_salesforce_contacts
image: python:3.11

secrets:
  - key: salesforce
    inject_as: SALESFORCE_CONNECTION
@bruin"""
```

Then use `scripts/salesforce_activation_client.py` as the reference implementation for building a `simple_salesforce.Salesforce` client from `SALESFORCE_CONNECTION`. It supports:

- OAuth access token connections.
- Connected-app client credentials used to mint an access token.
- Username/password/security-token login with My Domain fallback candidates.

Read `references/salesforce-bruin-auth.md` when adding or changing activation code.

### 4. Dry-run first

Every activation must produce a dry-run summary before live writes:

- Number of candidate records.
- Object and fields to be changed.
- Match key and unmatched-key count.
- Sample before/after values, with PII minimized.
- Expected creates, updates, skips, and known risks.

Use `DRY_RUN=1` or a task-specific dry-run environment variable. Never make dry-run mode depend on Slack prose alone.

### 5. Apply the change

Use the smallest safe mutation path:

- Prefer `update` by Salesforce `Id` when IDs are known and were just verified.
- Prefer `upsert` by a Salesforce external ID field when available.
- For natural keys that are not external IDs, query existing records first, then create/update explicitly.
- Use chunked writes and collect per-record errors.
- Use `allOrNone=false` semantics when using APIs that support it, unless atomic rollback is explicitly required.
- Stop on schema errors, auth failures, permission errors, unexpectedly high row counts, or source/destination count mismatches.

For admin or metadata work, snapshot current state first with SOQL, Tooling API, Metadata API, or Salesforce CLI. Do not modify profiles, permission sets, sharing rules, validation rules, flows, triggers, connected apps, or auth policies without explicit approval.

### 6. Verify and report

After writes:

- Query Salesforce for changed IDs or natural keys.
- Compare requested count vs success, failure, and skipped counts.
- Verify downstream Bruin ingestion or models when the change should appear in the warehouse.
- Record production commands, timing, run IDs, counts, blockers, and decisions in the client plan or handoff when the work is part of an implementation or migration.
- Reply in Slack with concise status, changed objects, counts, failures, and next action.

## References

- `references/salesforce-bruin-auth.md`: Bruin Salesforce connection and Python client pattern.
- `references/activation-guardrails.md`: approval gates, Slack response format, and safe mutation rules.
- `scripts/salesforce_activation_client.py`: reusable Python helper for SOQL probes and record writes.
