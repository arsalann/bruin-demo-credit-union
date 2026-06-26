# Activation Guardrails

## Approval gates

Require explicit approval after dry-run for:

- Deletes, merges, record conversions, deactivations, ownership changes, and mass reassignment.
- More than 100 Salesforce records, unless the user already approved an exact row count.
- Any change to `User`, `Profile`, `PermissionSet`, sharing, validation rules, flows, triggers, connected apps, login policy, or metadata.
- Writes where the source row count does not match the matched Salesforce row count.
- Writes into an org/environment that is not clearly identified.

For narrow, reversible field updates where the user already asked to apply the change, a dry-run summary and immediate execution is acceptable only if object, fields, match key, source, and row count are unambiguous.

## Required dry-run summary

Reply with:

```text
Dry run ready:
- Org: <org/environment>
- Object: <ObjectApiName>
- Operation: <create/update/upsert/admin>
- Match key: <Id/external id/natural key>
- Candidate records: <n>
- Expected creates/updates/skips: <n>/<n>/<n>
- Fields changing: <field list>
- Sample: <2-5 redacted before/after examples>
- Approval needed: <yes/no and reason>
```

## Safe write behavior

- Keep source snapshots or query outputs in `.context/` if needed for collaboration; do not commit them.
- Redact PII in Slack unless the requester supplied the exact values.
- Use chunked writes and capture per-record errors.
- Do not retry validation, permission, duplicate-rule, or schema failures blindly.
- Stop immediately on unexpected row count expansion.
- Prefer deactivation/status changes over deletes when the business request allows.

## Verification summary

After live writes, report:

```text
Salesforce activation complete:
- Object: <ObjectApiName>
- Requested: <n>
- Created: <n>
- Updated: <n>
- Skipped: <n>
- Failed: <n>
- Verification: <SOQL/Bruin query summary>
- Follow-up: <needed or none>
```
