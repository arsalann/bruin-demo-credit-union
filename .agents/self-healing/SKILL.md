---
name: self-healing-credit-union-pipeline
description: Investigate, classify, fix, and safely recover credit union Bruin Cloud pipeline failures for the Salesforce-to-Snowflake credit_union_dwh pipeline, including Salesforce schema drift, Snowflake SQL failures, quality checks, metric metadata fixes, and scoped Cloud reruns.
---

# Self-Healing credit union Pipeline

Use this skill when a Bruin Cloud agent or FDE is asked to investigate, fix, or
recover failures in the credit union `credit_union_dwh` Salesforce-to-Snowflake pipeline.

## When to use

Use for:

- Bruin Cloud run failures, failed checks, and stuck runs.
- Salesforce source schema drift or source value format changes.
- Snowflake SQL, privilege, schema, and cast errors.
- Incorrect metric labels or descriptions in gold assets.
- Scoped reruns or asset/downstream Cloud triggers after a fix.

Do not use for:

- Creating broad production backfills without approval.
- Editing or rotating credentials.
- Mutating Salesforce source data outside explicit scenario testing or human
  approval.
- Marking failed runs successful.

## Inputs

Required:

- Project ID or enough context to find it with `bruin cloud projects list`.
- Pipeline name, normally `credit_union_dwh`.

Optional:

- Run ID, asset name, interval, Cloud thread, Slack alert, or scenario name.

## Context to gather

Run read-only discovery first:

```bash
bruin cloud runs diagnose --project-id <project-id> --pipeline credit_union_dwh --latest --output json
bruin cloud instances failed-logs --project-id <project-id> --pipeline credit_union_dwh --run-id <run-id> --output json
bruin cloud assets get --project-id <project-id> --pipeline credit_union_dwh --asset <asset> --output json
bruin validate --fast pipelines/credit_union_dwh
```

Read the local asset and pipeline files before running or changing anything.
Use `bruin lineage <asset-file> --output json --full` when dependency impact is
unclear.

For Snowflake evidence, use read-only `bruin query --connection
snowflake-default` with a description. For Salesforce source evidence, prefer
Cloud logs and bronze ingestion behavior unless a human explicitly approves a
source query or mutation.

## Decision tree

```text
if auth/login/security-token/SOAP failure:
  classify salesforce-auth and escalate connection fix
elif source field appears/disappears or schema contract complains:
  classify salesforce-schema-drift
  if additive and bronze schema_contract is evolve:
    validate bronze ingestion and propagate requested downstream columns
  else:
    escalate before destructive or narrowing changes
elif Snowflake says invalid identifier/current schema/permission:
  classify snowflake-sql or snowflake-privilege
  fix SQL qualification/materialization only when local evidence proves it
elif Snowflake says numeric value not recognized or cast failed:
  classify salesforce-schema-drift when source value format changed
  widen downstream type or replace brittle cast
elif check failed:
  classify quality-fail and inspect failing rows
elif metric label or description is wrong:
  classify metric-definition and edit metadata/label only
elif retryable timeout/throttle/network:
  classify transient and rerun only failed assets
else:
  classify unknown and return evidence plus next question
```

## Actions and guardrails

Auto-allowed:

- Read Cloud runs, assets, instances, logs, validation errors, and glossary.
- Read local pipeline files.
- Run `bruin validate --fast`.
- Run read-only Snowflake evidence queries.
- Prepare a minimal repo fix for SQL metadata, casts, schema docs, or downstream
  propagation.

Allowed only after evidence supports it:

- `bruin cloud runs rerun --only-failed` for transient failures.
- `bruin cloud runs trigger --asset <asset> --downstream` for a narrow interval
  after a validated fix.

Requires human approval:

- Full refresh of Salesforce bronze assets.
- Source-system mutations.
- Cloud connection changes.
- Pipeline enable/disable/delete, run cancel/mark-status, or broad backfills.
- Type narrowing, column removal, or changes with unclear downstream blast
  radius.

Never allowed:

- Print secrets.
- Delete data to pass checks.
- Silence or weaken checks without approval.
- Invent a successful verification without a Cloud run, local validation, or
  warehouse evidence.

## Verification

After a code or metadata fix:

```bash
bruin validate --fast pipelines/credit_union_dwh
```

If Cloud action is allowed, verify with:

```bash
bruin cloud runs get --project-id <project-id> --pipeline credit_union_dwh --run-id <run-id> --output json
bruin cloud instances list --project-id <project-id> --pipeline credit_union_dwh --run-id <run-id> --output json
```

For downstream propagation, query Snowflake for the target column, non-null
count, and representative samples.

## Output

Write sanitized evidence to `.context/self-healing/<run-id>/` when useful.
Return run ID, failed asset, class, evidence, action, verification, and next
step.
