# Self-Healing Scenarios

These scripts create controlled issues for testing the credit union self-healing
agent. They do not run automatically and they dry-run unless `--apply` is set.

## Scenario 1: New Salesforce attribute

Create and populate `Opportunity.Credit_Union_Agent_Test_Tier__c`.

Expected agent behavior:

- Detect additive Salesforce schema drift.
- Confirm bronze `bronze.salesforce_opportunities` uses
  `schema_contract: evolve`.
- Trigger or recommend a scoped bronze/downstream run.
- Add downstream propagation only where requested.
- Verify the field is populated in Snowflake.

```bash
python3 .agents/self-healing/scenarios/self_healing_scenarios.py \
  salesforce new-attribute --apply --limit 25
```

Undo this scenario for a repeatable demo:

```bash
python3 .agents/self-healing/scenarios/self_healing_scenarios.py \
  salesforce new-attribute --revert --apply --limit 0 --delete-field
```

Omit `--delete-field` to keep the Salesforce custom field and only clear test
values. Use `--limit 0` to clear all matching Credit Union Demo Opportunity rows.
If the org blocks hard custom-field deletion, values are still cleared and the
field may remain. Use `--field-suffix <name>` on the next `new-attribute` run
to force a fresh additive field.

## Scenario 2: Integer-to-string format drift

Create/populate `Opportunity.Credit_Union_Agent_Test_Score__c` with string values
such as `SCORE-104`, then inject a local downstream model issue that casts it as
`INTEGER`.

Expected agent behavior:

- Use Cloud logs to identify a Snowflake cast failure.
- Inspect source values and local SQL.
- Change downstream metadata and SQL to `VARCHAR` instead of coercing the
  source to a fake number.
- Validate and rerun the narrow asset/downstream scope.

```bash
python3 .agents/self-healing/scenarios/self_healing_scenarios.py \
  salesforce score-format --apply --limit 25

python3 .agents/self-healing/scenarios/self_healing_scenarios.py \
  repo score-format --apply
```

Undo the local repo issue:

```bash
python3 .agents/self-healing/scenarios/self_healing_scenarios.py \
  repo score-format --revert
```

Undo the Salesforce source-data part:

```bash
python3 .agents/self-healing/scenarios/self_healing_scenarios.py \
  salesforce score-format --revert --apply --limit 0 --delete-field
```

## Scenario 3: Incorrect metric description

Change the `activity_coverage_pct` KPI label to an obviously wrong metric
description.

Expected agent behavior:

- Classify this as `metric-definition`.
- Fix the metric label or description without changing the SQL calculation
  unless evidence proves the calculation is wrong.

```bash
python3 .agents/self-healing/scenarios/self_healing_scenarios.py \
  repo metric-description --apply
```

Undo the local repo issue:

```bash
python3 .agents/self-healing/scenarios/self_healing_scenarios.py \
  repo metric-description --revert
```
