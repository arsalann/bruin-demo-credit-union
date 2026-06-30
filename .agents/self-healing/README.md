# Credit Union Self-Healing Agent

This folder contains the Bruin Cloud agent prompt and scenario harness for the
Credit Union Salesforce-to-Snowflake demo pipeline.

## Agent setup

Create a Bruin Cloud agent scoped to the `bruin-fde` project and give it:

- Bruin Cloud CLI access.
- A read-only Snowflake connection set for investigation.
- Salesforce connection visibility only through Bruin pipeline assets and Cloud
  run logs unless a human explicitly approves source-system changes.
- The system prompt in `cloud-agent-system-prompt.md`.

Recommended scheduled task:

```bash
Every 15 minutes, inspect the latest credit_union_dwh runs. If any run failed or has
failed checks, diagnose it, classify the failure, write an evidence summary, and
recommend or perform only the allowed action from the guardrails.
```

The agent may rerun failed Cloud assets when the diagnosis shows a transient
Salesforce, Snowflake, or network failure. It must not full-refresh Salesforce
bronze assets, alter source-system data, mark runs successful, or mutate Cloud
connections without human approval.

## Scenario harness

Use `scenarios/self_healing_scenarios.py` to create controlled failures:

```bash
python3 .agents/self-healing/scenarios/self_healing_scenarios.py \
  salesforce new-attribute --apply --limit 25

python3 .agents/self-healing/scenarios/self_healing_scenarios.py \
  salesforce score-format --apply --limit 25

python3 .agents/self-healing/scenarios/self_healing_scenarios.py \
  repo score-format --apply

python3 .agents/self-healing/scenarios/self_healing_scenarios.py \
  repo metric-description --apply
```

All commands dry-run by default. The repo mutations are marker-based and can be
reverted. Salesforce scenarios can also be undone so the demo can be repeated:

```bash
python3 .agents/self-healing/scenarios/self_healing_scenarios.py \
  salesforce new-attribute --revert --apply --limit 0 --delete-field

python3 .agents/self-healing/scenarios/self_healing_scenarios.py \
  salesforce score-format --revert --apply --limit 0 --delete-field

python3 .agents/self-healing/scenarios/self_healing_scenarios.py \
  repo score-format --revert

python3 .agents/self-healing/scenarios/self_healing_scenarios.py \
  repo metric-description --revert
```

Omit `--delete-field` when you only want to clear the test values but keep the
Salesforce custom field. Use `--limit 0` to clear all matching Credit Union Demo
Opportunity rows.

Some Salesforce orgs block hard custom-field deletion through Tooling API after
the field is created. In that case the script still exits cleanly after clearing
values and prints the deletion blocker. For a fresh additive-field demo, pass a
suffix:

```bash
python3 .agents/self-healing/scenarios/self_healing_scenarios.py \
  salesforce new-attribute --apply --limit 25 --field-suffix demo2
```

Run Bruin validation before using a scenario in Cloud:

```bash
bruin validate --fast pipelines/credit_union_dwh
```

Then trigger the smallest Cloud run needed for the scenario, for example:

```bash
bruin cloud runs trigger \
  --project-id 01kvqkcm7pg35gcggxwdrkx7hf \
  --pipeline credit_union_dwh \
  --asset bronze.salesforce_opportunities \
  --downstream \
  --start-date 2026-06-23 \
  --end-date 2026-06-24 \
  --note "self-healing scenario: opportunity schema drift" \
  --output json
```
