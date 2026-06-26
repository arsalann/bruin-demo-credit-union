# Credit Union Handoff

## Goal

Build and operationalize a credit union demo project for a California credit union
that shows a Bruin-managed Salesforce CRM analytics workflow:

- Generate realistic Salesforce demo data from `2015-01-01` forward.
- Ingest Salesforce `Account`, `Contact`, `Opportunity`, and `Task` objects into
  Snowflake.
- Model bronze CRM data into governed silver and gold analytics layers.
- Keep regular daily runs interval-scoped so they generate and process only new
  interval data.
- Prepare Bruin Cloud agent context for self-healing and Snowflake cost
  optimization.

## Current State

- Active pipeline: `pipelines/credit_union_dwh/`.
- Active destination: Snowflake connection `snowflake-default`.
- Pipeline start date: `2015-01-01`.
- Pipeline schedule: daily.
- Historical full-refresh seed now generates every date in the requested Bruin
  interval. A full 2015 backfill will create or update thousands of Salesforce
  records at the default 1/1/1/1 object volume.
- Explicit daily runs must use exclusive end dates. Example:
  `--start-date 2026-06-22 --end-date 2026-06-23`.
- BigQuery prototype was retired and deleted after Snowflake end-to-end
  verification.
- The clean 2015 full refresh passed on 2026-06-22:
  - Command:
    `CREDIT_UNION_ACCOUNTS_PER_DAY=1 CREDIT_UNION_CONTACTS_PER_ACCOUNT=1 CREDIT_UNION_OPPORTUNITIES_PER_ACCOUNT=1 CREDIT_UNION_TASKS_PER_OPPORTUNITY=1 bruin run --full-refresh --start-date 2015-01-01 --end-date 2026-06-23 pipelines/credit_union_dwh`
  - Result: 11 assets succeeded, 72 quality checks succeeded, runtime 7m41s.
  - Seed updated 301 Accounts, 301 Contacts, 301 Opportunities, and 301 Tasks;
    0 creates and 0 errors.
- Normal daily run also passed on 2026-06-22:
  - Command:
    `CREDIT_UNION_ACCOUNTS_PER_DAY=1 CREDIT_UNION_CONTACTS_PER_ACCOUNT=1 CREDIT_UNION_OPPORTUNITIES_PER_ACCOUNT=1 CREDIT_UNION_TASKS_PER_OPPORTUNITY=1 bruin run --start-date 2026-06-22 --end-date 2026-06-23 pipelines/credit_union_dwh`
  - Result: 11 assets succeeded, 72 quality checks succeeded, runtime 18s.
  - Seed updated exactly 1 generated Account, Contact, Opportunity, and Task; 0
    creates.
- Latest verified Snowflake row counts:
  - `BRONZE.SALESFORCE_ACCOUNTS`: 470
  - `BRONZE.SALESFORCE_CONTACTS`: 477
  - `BRONZE.SALESFORCE_OPPORTUNITIES`: 499
  - `BRONZE.SALESFORCE_TASKS`: 468
  - `SILVER.SALESFORCE_ACCOUNT_HEALTH`: 470
  - `SILVER.SALESFORCE_OPPORTUNITY_PIPELINE`: 499
  - `GOLD.PIPELINE_KPIS`: 4
  - `GOLD.PIPELINE_BY_STAGE`: 5
  - `GOLD.PIPELINE_BY_CHANNEL_MONTHLY`: 167
  - `GOLD.ACTIVITY_COVERAGE_BY_PRODUCT`: 6
- Generated demo key coverage spans `CREDIT-UNION-DEMO-20150101-001` through
  `CREDIT-UNION-DEMO-20260622-001`.
- Duplicate check for June 22 generated rows returned exactly 1 Opportunity and
  1 Task after cleanup.
- Bruin Cloud CLI authentication works through local `.bruin.yml`
  `bruin-cloud`; the credit union pipeline is under project
  `01kvqkcm7pg35gcggxwdrkx7hf` (`bruin-fde`).
- Bruin Cloud now runs merged asset version
  `425cb4bedc51ffeb35478490b32e939e4ffb0b02`.
- Earlier Cloud runs failed on Salesforce auth (`INVALID_SESSION_ID`,
  `INVALID_LOGIN`, and SOAP API login disabled). After enabling SOAP API login
  in Salesforce, username/password/security-token auth worked in Cloud.
- Local Salesforce OAuth client credentials were tested directly against the
  Salesforce token endpoint and succeeded, but Bruin ingestr did not accept the
  direct `grant_type: client_credentials` / `client_id` / `client_secret`
  connection shape. `bronze.salesforce_accounts` failed with
  `username is required for Salesforce` until local `.bruin.yml` was updated to
  the Bruin-documented `access_token` shape. The rerun fetched 457 Salesforce
  Account rows, merged them into Snowflake, and passed all 6 quality checks.
- Local `.bruin.yml` was later changed to keep only one `salesforce` connection
  using username/password/security token. Bruin validation passed, but the real
  ingestr run initially failed because the Salesforce org blocked SOAP login:
  `INVALID_OPERATION: SOAP API login() is disabled by default in this org.`
- Earlier Bruin Cloud run after updating the Cloud Salesforce connection:
  - Run ID: `scheduled__2026-06-22T00:00:00+00:00`
  - Started: `2026-06-23 11:58:48Z`
  - Status: failed after 51s.
  - Root failed asset: `bronze.seed_salesforce_demo_data`.
  - Downstream assets: `upstream_failed`.
  - Root error: `SalesforceAuthenticationFailed: Authentication failed (code:
    INVALID_LOGIN): Invalid username, password, security token; or user locked
    out.`
  - This run used stale asset version commit `146de563...`.
- Manual Cloud retry after the branch was pushed and merged:
  - First retry: `manual__2026-06-23T12:22:34+00:00`.
  - Result: failed after 22s because the trigger used undeclared `--var`
    overrides (`CREDIT_UNION_ACCOUNTS_PER_DAY` etc.). This was a bad trigger command,
    not an asset failure.
  - Clean retry: `manual__2026-06-23T12:23:19+00:00`.
  - Result: failed after 53s.
  - Asset version: `425cb4bedc51ffeb35478490b32e939e4ffb0b02`, so Cloud is now
    using the merged code.
  - Seed plan confirmed the expected daily 1/1/1/1 volume for `2026-06-22`.
  - Root error remains Salesforce auth:
    `SalesforceAuthenticationFailed: Authentication failed (code:
    INVALID_LOGIN): Invalid username, password, security token; or user locked
    out.`
- User-triggered Cloud run for `bronze.salesforce_accounts`:
  - Run ID: `manual__2026-06-23T12:29:04+00:00`.
  - Asset version: `425cb4bedc51ffeb35478490b32e939e4ffb0b02`.
  - Root error from ingestr/simpleforce:
    `failed to connect to source: failed to login to Salesforce` and
    `INVALID_OPERATION: SOAP API login() is disabled by default in this org.`
  - This confirms Cloud username/password/security-token auth is blocked for
    the Salesforce org; it is not specific to the seed asset.
- After Salesforce SOAP API login was enabled, manual Cloud run
  `manual__2026-06-23T13:28:24+00:00` made it past Salesforce:
  - `bronze.seed_salesforce_demo_data`: success.
  - `bronze.salesforce_accounts`, `contacts`, `opportunities`, `tasks`: success.
  - `silver.salesforce_account_health` and
    `silver.salesforce_opportunity_pipeline`: success.
  - Gold assets `activity_coverage_by_product`, `pipeline_by_stage`, and
    `pipeline_kpis`: success.
  - Only failure: `gold.pipeline_by_channel_monthly`.
  - Root error: Snowflake `Cannot perform CREATE TEMPTABLE. This session does
    not have a current schema. Call 'USE SCHEMA', or use a qualified name.`
  - Local fix implemented: changed the asset from Bruin `delete+insert` to
    `create+replace` table materialization, avoiding the unqualified temp table.
    Local single-asset run passed with all 6 checks.
- Added `gold.pipeline_by_channel_daily` as the pipeline's Bruin
  `time_interval` example. It uses `close_date` with `time_granularity: date`.
  A first normal local run failed because the target table did not exist, then
  `--full-refresh` bootstrapped it and the following normal interval run passed.
- Expanded the Salesforce demo to a fuller industry-standard CRM pipeline:
  Users, Leads, Campaigns, Products, Pricebooks, PricebookEntries,
  OpportunityContactRoles, OpportunityLineItems, and Events now exist in the
  pipeline alongside Accounts, Contacts, Opportunities, and Tasks.
- Latest local end-to-end run on 2026-06-23 for interval `2026-06-23` to
  `2026-06-24` passed: 29 assets succeeded and 138 quality checks succeeded in
  33.31s.
- Agent context now lives under `.agents/`. The self-healing agent
  context is present, and the new `data-activation-salesforce-admin` skill is
  ready for Bruin Slack agent use.
- The self-healing scenario harness supports repeatable demos. Salesforce
  source-data scenarios can be reset with `--revert`; add `--delete-field` to
  remove the scenario custom field after clearing demo Opportunity values.
- The self-healing skill and scenario harness have been tested. Skill
  validation passes, repo scenario apply/revert loops leave no residual asset
  diffs, Salesforce dry-run apply/revert paths connect successfully, and mocked
  Salesforce tests cover field create/delete plus Opportunity populate/clear.
- After the Snowflake key was restored, `bruin validate --fast
  pipelines/credit_union_dwh` passes for all 29 assets.
- Live self-healing Salesforce scenario tests ran with `--apply --limit 1` for
  both `new-attribute` and `score-format`. The script created or reused the
  scenario custom fields, granted current-profile FieldPermissions, updated one
  Opportunity, then reverted values. Verification found 0 Credit Union Demo
  Opportunities with either scenario field populated.
- This Salesforce org blocks hard deletion of the scenario custom fields via
  Tooling API with `INSUFFICIENT_ACCESS_ON_CROSS_REFERENCE_ENTITY`. The script
  now treats field deletion as best-effort, clears values, exits cleanly, and
  documents `--field-suffix` for fresh additive-field repeat demos.
- As of 2026-06-24, the data activation Salesforce admin skill has been tested
  end to end through the safe path: mocked helper tests, Bruin skill validation,
  pipeline validation, and a live read-only Salesforce credential probe through
  Bruin secret injection. No live Salesforce write was performed during this
  data-activation skill test.
- Demo decision for the self-healing walkthrough: delete only the last 10 days
  of namespaced credit union demo source rows, let the user create 10 daily Bruin
  Cloud runs from `main` to regenerate that window, then inject failures and ask
  the Slack agent to diagnose and self-heal. Bruin Cloud runs the pipeline code
  from `main`, so any intentional repo-based failure must be committed and
  deployed to `main` before Cloud can fail on it.
- The June 24, 2026 demo reset has been applied for `2026-06-14` through
  exclusive end `2026-06-24`. Salesforce deletes removed 10 Accounts, 10
  Contacts, 10 Leads, 10 Opportunities, 10 Tasks, 10 Events, 10
  OpportunityLineItems, and 11 OpportunityContactRoles. Snowflake cleanup
  removed the matching bronze rows plus 10 silver account-health rows, 10 silver
  opportunity rows, 10 silver product-pipeline rows, and 20 silver activity
  rows. Verification returned 0 remaining rows for the reset window in
  Salesforce and Snowflake bronze/silver.
- Scenario 1 additive schema drift has been applied for the June 15 demo. The
  script created `Opportunity.Credit_Union_Agent_Test_Tier_june15__c`, granted
  FieldPermissions, and populated 25 Credit Union Demo Opportunity rows. A Cloud run
  was triggered for the June 15 interval using Bruin's exclusive end convention:
  `2026-06-15T00:00:00Z` to `2026-06-16T00:00:00Z`. Run ID:
  `manual__2026-06-24T13:30:43+00:00`; status was `running` at first poll.
- Scenario 2 score-format setup is active in Cloud. Salesforce field
  `Opportunity.Credit_Union_Agent_Test_Score__c` exists, FieldPermissions were
  updated, and 25 Credit Union Demo Opportunity rows were populated with string score
  values. PR #13 merged the repo-side scenario mutation to `main` at
  `ab3f499`, adding intentional integer typing and casting in
  `bronze.salesforce_opportunities` and `silver.salesforce_opportunity_pipeline`.
  A Cloud run was triggered for `2026-06-16T00:00:00Z` to
  `2026-06-17T00:00:00Z`; run ID: `manual__2026-06-24T13:59:14+00:00`.
  Final Cloud status is `failed`; run started `2026-06-24 13:59:14Z`, ended
  `2026-06-24 14:05:40Z`, and wall time was `00:06:26`.
  `silver.salesforce_opportunity_pipeline` failed as intended with Snowflake
  query `01c543cb-0000-60f3-0001-003e0006c732`: SQL compilation error at
  line 134, position 193, invalid identifier `AGENT_TEST_SCORE`.
- Scenario 3 metric-definition recovery is complete. PR #21 restored the
  `gold.pipeline_kpis` display label for `activity_coverage_pct` from
  `Average approved loan APR` to `Opportunities with activity`; the metric key
  and SQL calculation remain unchanged. Scoped Cloud run
  `manual__2026-06-24T19:02:03+00:00` refreshed only `gold.pipeline_kpis` for
  the June 23-24 interval and succeeded in `00:00:18`. Snowflake verification
  returned `activity_coverage_pct`, `Opportunities with activity`, `0.846535`.

## Files In Flight

- `.gitignore`
- `PLAN.md`
- `handoff.md`
- `pipelines/credit_union_dwh/README.md`
- `pipelines/credit_union_dwh/pipeline.yml`
- `pipelines/credit_union_dwh/assets/bronze/seed_salesforce_demo_data.py`
- `pipelines/credit_union_dwh/assets/bronze/*.asset.yml`
- `pipelines/credit_union_dwh/assets/bronze/salesforce_campaign_members.sql`
- `pipelines/credit_union_dwh/assets/silver/*.sql`
- `pipelines/credit_union_dwh/assets/gold/*.sql`
- `pipelines/credit_union_dwh/assets/gold/pipeline_by_channel_daily.sql`
- `.agents/self-healing/README.md`
- `.agents/self-healing/SKILL.md`
- `.agents/self-healing/cloud-agent-system-prompt.md`
- `.agents/self-healing/scenarios/README.md`
- `.agents/self-healing/scenarios/self_healing_scenarios.py`
- `.agents/data-activation-salesforce-admin/SKILL.md`
- `.agents/data-activation-salesforce-admin/agents/openai.yaml`
- `.agents/data-activation-salesforce-admin/references/activation-guardrails.md`
- `.agents/data-activation-salesforce-admin/references/salesforce-bruin-auth.md`
- `.agents/data-activation-salesforce-admin/scripts/salesforce_activation_client.py`
- `.context/test_data_activation_salesforce_admin.py`
- `.context/data_activation_salesforce_probe.py`
- `.context/requirements.txt`
- `.context/test_self_healing_scenarios.py`
- `.context/self-healing-scenarios/*.json`

## Changed

- Set `credit_union_dwh` pipeline start date to `2015-01-01`.
- Updated `.gitignore` to ignore Bruin run logs under `logs/runs`.
- Refactored `seed_salesforce_demo_data.py`:
  - no Python materialization;
  - interval-driven deterministic Salesforce upserts;
  - 2015-compatible generation;
  - full-refresh generation for every date in the requested Bruin interval;
  - exclusive-end-date handling for Bruin intervals;
  - deterministic contact/opportunity/task keys stable across full-refresh and
    daily windows;
  - fail-fast handling for Salesforce `STORAGE_LIMIT_EXCEEDED`.
- Removed the sparse historical generation limiter. Dry-run verification for
  `2015-01-01` to `2026-06-23` now plans 4,191 generated days and 4,191 rows per
  Salesforce object at 1/1/1/1 volume, with no Salesforce writes in dry-run mode.
- Optimized materialization and incremental strategy:
  - bronze ingestr assets use `incremental_strategy: merge`,
    `incremental_key: SystemModstamp`, schema enforcement, snake_case schema
    naming, and Snowflake clustering;
  - silver account/opportunity marts use Bruin SQL `merge` and only recompute
    records touched by source `SystemModstamp` in the Bruin interval on normal
    runs;
  - added `gold.pipeline_by_channel_daily` with Bruin `time_interval`
    materialization on `close_date`;
  - `gold.pipeline_by_channel_monthly` now uses `create+replace` table
    materialization;
  - broad gold dashboard rollups are views over current silver tables.
- Added metadata, tags, domains, and safe quality checks across bronze, silver,
  and gold assets.
- Removed invalid `incremental_key` fields from SQL `merge` materializations
  after Bruin validation rejected them.
- Refreshed local Salesforce OAuth token in gitignored `.bruin.yml` without
  printing the token.
- Minted a Salesforce access token from the connected app client credentials
  without printing it, set local `salesforce` to the Bruin-supported
  `access_token` shape, and preserved the durable client credentials locally as
  `salesforce-client-credentials` for future token refresh work.
- Replaced the local Salesforce connection with a single username/password/token
  connection named `salesforce` when testing the Bruin-documented durable auth
  option. This is currently blocked by Salesforce org policy, not by Bruin
  validation.
- Deleted one unintended duplicate June 22 Opportunity and related Task from
  Salesforce after a failed same-day smoke test created alternate product rows.
- Ran clean 2015 full refresh and normal daily interval successfully.
- Updated `README.md`, `PLAN.md`, and this handoff with the successful run
  commands, counts, and operational notes.
- Updated Cloud operational notes after Salesforce SOAP API login was enabled:
  the Salesforce connection now works in Cloud, and the remaining Cloud blocker
  was Snowflake current schema for `gold.pipeline_by_channel_monthly`.
- Fixed `gold.pipeline_by_channel_monthly` locally by switching from
  `delete+insert` to `create+replace`; local run passed with all 6 checks.
- Added and locally verified `gold.pipeline_by_channel_daily`:
  `bruin validate --fast pipelines/credit_union_dwh` passed for 12 assets;
  `bruin run --full-refresh --start-date 2026-06-22 --end-date 2026-06-23 .../pipeline_by_channel_daily.sql`
  passed; the subsequent normal interval run for the same window passed.
- Refactored `seed_salesforce_demo_data.py` to seed more Salesforce standard
  objects for credit union:
  - Leads for acquisition funnel demos;
  - Products and PricebookEntries for product-grain pipeline;
  - OpportunityContactRoles for member decision-maker roles;
  - OpportunityLineItems for loan/deposit/card product analytics;
  - Events for branch/video appointments;
  - Campaign generation with createability detection, because this org blocks
    Campaign inserts for the current user.
- Added bronze Salesforce assets for `user`, `lead`, `campaign`, `product`,
  `pricebook`, `pricebook_entry`, `opportunity_contact_role`,
  `opportunity_line_item`, and `event`.
- Replaced `bronze.salesforce_campaign_members` with a source-shaped empty SQL
  table. The Salesforce org has no campaign members and ingestr currently fails
  on empty CampaignMember extracts with the snake_case incremental-key path.
- Added silver models:
  - `silver.salesforce_product_pipeline`;
  - `silver.salesforce_marketing_funnel`;
  - `silver.salesforce_activity_timeline`.
- Added gold models:
  - `gold.product_pipeline_performance`;
  - `gold.campaign_conversion_funnel`;
  - `gold.branch_relationship_health`;
  - `gold.banker_activity_coverage`.
- Added credit union self-healing agent context under
  `.agents/self-healing/`:
  - Bruin Cloud agent setup README;
  - paste-ready Cloud agent system prompt;
  - local SKILL/runbook using the 7-section contract;
  - scenario README;
  - dry-run-first scenario harness for Salesforce Opportunity additive fields,
    string-format schema drift, and incorrect KPI metric labels;
  - Salesforce `--revert` cleanup path with optional custom-field deletion for
    repeatable demos.
- Added credit union data activation and Salesforce admin skill under
  `.agents/data-activation-salesforce-admin/`:
  - Slack-agent workflow for activating approved warehouse or user-provided data
    into Salesforce;
  - Bruin/Salesforce auth reference using the same `SALESFORCE_CONNECTION`
    injection pattern as `bronze.seed_salesforce_demo_data`;
  - activation guardrails for dry-run summaries, approval gates, scoped writes,
    safe admin changes, and post-write verification;
  - reusable `salesforce_activation_client.py` helper supporting OAuth access
    token, connected-app client-credentials token minting, and
    username/password/security-token auth shapes without printing secrets.
- Hardened the data activation helper after mocked testing:
  - missing Salesforce `Id` matches now skip with an error instead of creating a
    record when `match_field` is `Id`;
  - My Domain fallback no longer tries the bogus `.my`-stripped candidate for
    hosts ending in `.my.salesforce.com`;
  - failed domain candidates now log at debug level, so successful fallback auth
    does not produce noisy run logs.
- Ran normal expanded pipeline command:
  `CREDIT_UNION_ACCOUNTS_PER_DAY=1 CREDIT_UNION_CONTACTS_PER_ACCOUNT=1 CREDIT_UNION_OPPORTUNITIES_PER_ACCOUNT=1 CREDIT_UNION_TASKS_PER_OPPORTUNITY=1 CREDIT_UNION_LEADS_PER_DAY=1 CREDIT_UNION_EVENTS_PER_OPPORTUNITY=1 bruin run --start-date 2026-06-23 --end-date 2026-06-24 pipelines/credit_union_dwh`.
  Result: 29 assets succeeded and 138 checks succeeded in 33.31s.
- Verified Snowflake counts after the expanded run:
  bronze Accounts 590, Contacts 478, Leads 24, Campaigns 4, CampaignMembers 0,
  Users 8, Products 26, Pricebooks 2, PricebookEntries 43, Opportunities 502,
  OpportunityContactRoles 2, OpportunityLineItems 2, Tasks 471, Events 2; silver
  AccountHealth 590, OpportunityPipeline 502, ProductPipeline 2,
  MarketingFunnel 0, ActivityTimeline 473; gold ActivityCoverageByProduct 6,
  BankerActivityCoverage 1, BranchRelationshipHealth 20,
  CampaignConversionFunnel 0, PipelineByChannelDaily 281,
  PipelineByChannelMonthly 167, PipelineByStage 5, PipelineKPIs 4,
  ProductPipelinePerformance 2.

## Failed Attempts

- Initial `bruin validate --fast pipelines/credit_union_dwh` was blocked
  because `.credentials/credit-union/snowflake/rsa_key.p8` was missing.
- Initial requested 2015 full refresh was blocked by the same missing Snowflake
  key before any Salesforce/Snowflake changes.
- After credentials were restored, first full-refresh attempt failed at
  `bronze.seed_salesforce_demo_data` with Salesforce `INVALID_SESSION_ID`.
  Fixed by refreshing OAuth from Salesforce CLI.
- `bruin ai enhance --codex` hung in a nested Codex provider process and was
  killed.
- `bruin ai enhance --claude` failed because Bruin selected a Claude model that
  was unavailable locally.
- `bruin ai enhance --claude --model claude-sonnet-4-5-20250929` reached
  validation but stopped while the Snowflake key was still missing.
- Bruin validation rejected `incremental_key` on SQL `merge` materializations.
  Fixed by removing those fields and keeping interval pruning in SQL.
- A daily smoke run with equal `--start-date 2026-06-22 --end-date 2026-06-22`
  failed because ingestr requires interval start earlier than interval end.
  Use exclusive end dates instead.
- That failed smoke created one alternate June 22 Opportunity and Task before
  downstream ingestion failed. Both were deleted from Salesforce, then the clean
  full refresh removed them from Snowflake.
- Historical context: an earlier high-volume Salesforce seed hit
  `STORAGE_LIMIT_EXCEEDED`; now that the sparse historical limiter is removed,
  confirm Salesforce storage before running a full 2015 backfill.
- Earlier Bruin Cloud troubleshooting was blocked by the wrong token. After
  token correction, Cloud logs became available under project
  `01kvqkcm7pg35gcggxwdrkx7hf`.
- Direct Salesforce client credentials in `.bruin.yml` were not enough for
  Bruin ingestr. The actual Bruin run failed with `username is required for
  Salesforce`; use the documented `access_token` or username/password/security
  token connection shapes until Bruin ingestr supports client credentials.
- Username/password/security-token auth failed while SOAP API login was disabled
  in Salesforce. Enabling SOAP API login fixed the Cloud Salesforce auth path.
- Bruin Cloud failed at `gold.pipeline_by_channel_monthly` because Snowflake had
  no current schema for Bruin's `delete+insert` temp table. The local asset now
  avoids that strategy.
- First local normal run of `gold.pipeline_by_channel_daily` failed because
  Bruin `time_interval` expects an existing target table for interval delete and
  insert. Bootstrap with `--full-refresh` fixed it.
- An attempted pipeline `--full-refresh --start-date 2026-06-22 --end-date
  2026-06-23` expanded to the pipeline start `2015-01-01` and planned 4,191
  rows per interval object. It was killed to avoid filling the Salesforce dev
  org; only `bronze.salesforce_users` completed before termination and the seed
  asset exited with signal 143.
- First expanded daily seed failed because Campaign insert returned
  `entity type cannot be inserted: Campaign`. The seed now checks object
  createability and skips Campaign/CampaignMember creation without failing.
- Ingestr failed on empty `campaign_member` extraction with invalid identifier
  `SYSTEMMODSTAMP`. Replaced that asset with a source-shaped empty Snowflake SQL
  table until CampaignMember rows are available.
- Latest self-healing validation attempt:
  - `python3 /Users/bear/.codex/skills/.system/skill-creator/scripts/quick_validate.py .agents/self-healing`
    passed after adding required YAML frontmatter to `SKILL.md`.
  - `python3 -m py_compile .agents/self-healing/scenarios/self_healing_scenarios.py`
    passed.
  - `python3 .agents/self-healing/scenarios/self_healing_scenarios.py salesforce --help`
    shows `--revert` and `--delete-field` for repeatable Salesforce scenario
    cleanup.
  - Repo scenario apply/revert loops passed:
    `score-format` inserted and removed the intentional bronze/silver bad-cast
    changes with no residual asset diff; `metric-description` changed and
    restored the KPI label with no residual asset diff.
  - Salesforce dry-run apply commands connected and planned custom field
    creation plus one Opportunity update for both `new-attribute` and
    `score-format`.
  - Salesforce dry-run revert originally failed when the scenario custom field
    was absent. Fixed `_clear_opportunity_field` to no-op when the field is
    absent; both Salesforce revert dry-runs then passed.
  - `.context/test_self_healing_scenarios.py` mocked tests passed. They cover
    custom field create/delete, Opportunity populate/clear, and absent-field
    revert no-op without live Salesforce writes.
  - After credentials were restored,
    `bruin validate --fast pipelines/credit_union_dwh` passed for all 29
    assets.
  - Live Salesforce scenario tests passed for one-row apply/revert flows. The
    script found a real metadata propagation/FLS issue, so it now grants
    FieldPermissions to the current profile and waits for REST describe
    visibility before updating Opportunity rows.
  - Live cleanup verified 0 non-null values remained in
    `Credit_Union_Agent_Test_Tier__c` and `Credit_Union_Agent_Test_Score__c`.
  - Salesforce blocks hard custom-field deletion through the tested Tooling API
    path, so the fields may remain in the org with null values. Use
    `--field-suffix` for a fresh new-attribute demo when needed.
- Data activation skill validation:
  - `python3 -m py_compile .agents/data-activation-salesforce-admin/scripts/salesforce_activation_client.py`
    passed with the available local Python.
  - `python3 /Users/bear/.codex/skills/.system/skill-creator/scripts/quick_validate.py .agents/data-activation-salesforce-admin`
    passed with `Skill is valid!`.
  - `uv run --with simple-salesforce --with requests python3 .context/test_data_activation_salesforce_admin.py`
    passed. The mocked suite covers required files, Bruin secret-injection
    instructions, all supported Salesforce auth shapes, My Domain fallback,
    SOQL lookup batching, dry-run counts, live create/update calls, and
    missing-`Id` safety. It made no live Salesforce writes.
  - Live read-only Bruin probe passed after credentials were added. `bruin
    connections test --name salesforce` still reports that this connection type
    does not support testing, so a temporary Bruin Python asset was run under
    `pipelines/credit_union_dwh/assets/bronze/` and removed afterward. It
    authenticated via Bruin-injected `SALESFORCE_CONNECTION`, queried
    `Organization`, queried one `Account`, used `query_existing_by_field`,
    dry-ran an existing-`Id` update, and dry-ran a missing-`Id` update. Sanitized
    result: `org_probe_rows=1`, `account_probe_rows=1`, `query_existing_rows=1`,
    `dry_existing_update_count=1`, `dry_missing_id_created_count=0`,
    `dry_missing_id_skipped_count=1`, `live_writes=0`.
  - After the temporary probe asset was removed,
    `bruin validate --fast pipelines/credit_union_dwh` passed for the normal
    29-asset pipeline.
  - `python3.11` is not installed locally, so exact Python 3.11 compile could
    not be run; the helper avoids 3.12-only syntax.

## Demo Plan

Decision: delete only the last 10 days of namespaced credit union demo source rows,
then show a clean-to-broken-to-healed story in Bruin Cloud. Cloud executes code
from `main`, so Cloud-visible failures must come from code that has been
pushed/merged to `main`, not from an uncommitted local scenario patch.

### Stage 0: Prepare

1. Confirm local validation is clean:
   `bruin validate --fast pipelines/credit_union_dwh`.
2. Confirm no scenario values are currently populated in Salesforce:
   `Credit_Union_Agent_Test_Tier__c` and `Credit_Union_Agent_Test_Score__c` should have 0
   non-null Credit Union Demo Opportunity rows.
3. Reset Salesforce demo data before the demo by deleting only the last 10 days
   of namespaced credit union demo rows. For the June 24, 2026 demo, delete generated
   rows for `2026-06-14` through `2026-06-23`; do not delete older credit union demo
   rows and do not delete non-credit union org data.
4. Keep the date window small to avoid Salesforce storage problems. Recommended
   clean history window for the June 24, 2026 demo:
   `2026-06-14` through exclusive end `2026-06-24`.

### Stage 1: Build Healthy History

The user will run 10 successful daily Cloud intervals. Use `--split day` so
Cloud creates one run per day:

```bash
bruin cloud runs trigger \
  --project-id 01kvqkcm7pg35gcggxwdrkx7hf \
  --pipeline credit_union_dwh \
  --start-date 2026-06-14 \
  --end-date 2026-06-24 \
  --split day \
  --note "demo baseline: 10 daily healthy runs" \
  --output json
```

If Cloud needs a smaller bootstrap, use the same range with selected assets and
`--downstream`, but prefer whole-pipeline daily runs for the demo narrative.

### Stage 2: Additive Schema Drift Story

Create a new Opportunity field and populate it. Use a suffix if the base test
field already exists because Salesforce blocks hard custom-field deletion in
this org:

```bash
python3 .agents/self-healing/scenarios/self_healing_scenarios.py \
  salesforce new-attribute --apply --limit 25 --field-suffix demo1
```

Trigger the narrow Cloud run:

```bash
bruin cloud runs trigger \
  --project-id 01kvqkcm7pg35gcggxwdrkx7hf \
  --pipeline credit_union_dwh \
  --asset bronze.salesforce_opportunities \
  --downstream \
  --start-date 2026-06-23 \
  --end-date 2026-06-24 \
  --note "demo: additive Salesforce schema drift" \
  --output json
```

Expected story: bronze has `schema_contract: evolve`, so this should be
diagnosed as additive schema drift and downstream propagation work, not
necessarily a hard pipeline outage.

### Stage 3: Real Failure Story

Use the `score-format` scenario for an actual failure. Because Cloud runs code
from `main`, the intentionally bad repo change must be committed and deployed to
`main` before triggering Cloud.

1. Apply the repo failure:

   ```bash
   python3 .agents/self-healing/scenarios/self_healing_scenarios.py \
     repo score-format --apply
   ```

2. Commit/push/merge that intentional bad-cast version to `main`.
3. Populate Salesforce score strings:

   ```bash
   python3 .agents/self-healing/scenarios/self_healing_scenarios.py \
     salesforce score-format --apply --limit 25
   ```

4. Trigger Cloud:

   ```bash
   bruin cloud runs trigger \
     --project-id 01kvqkcm7pg35gcggxwdrkx7hf \
     --pipeline credit_union_dwh \
     --asset bronze.salesforce_opportunities \
     --downstream \
     --start-date 2026-06-23 \
     --end-date 2026-06-24 \
     --note "demo: string score drift causing downstream cast failure" \
     --output json
   ```

5. Ask Slack agent:
   `credit_union_dwh just failed after the Salesforce score-format scenario. Diagnose the failure, fix the repo, validate, and tell me the narrow Cloud rerun command.`

Expected fix: change the scenario score handling from integer/cast to string,
validate, merge fix to `main`, then rerun only the failed/downstream scope in
Cloud.

### Stage 4: Metric Definition Story

This is a semantic correction demo, not a pipeline outage:

```bash
python3 .agents/self-healing/scenarios/self_healing_scenarios.py \
  repo metric-description --apply
```

Commit/push/merge the intentionally wrong metric label to `main`, then ask Slack
agent:
`The activity coverage KPI description looks wrong. Inspect the credit union pipeline and fix the metric metadata without changing the calculation unless evidence shows the SQL is wrong.`

### Cleanup

After the demo:

```bash
python3 .agents/self-healing/scenarios/self_healing_scenarios.py \
  repo score-format --revert

python3 .agents/self-healing/scenarios/self_healing_scenarios.py \
  repo metric-description --revert

python3 .agents/self-healing/scenarios/self_healing_scenarios.py \
  salesforce new-attribute --revert --apply --limit 0 --delete-field --field-suffix demo1

python3 .agents/self-healing/scenarios/self_healing_scenarios.py \
  salesforce score-format --revert --apply --limit 0 --delete-field
```

The Salesforce custom fields may remain because the org blocks hard deletion via
Tooling API. The important cleanup check is 0 non-null Credit Union Demo Opportunity
rows for the scenario fields.

## Next Steps

1. Keep using exclusive end dates for explicit daily runs, e.g.
   `--start-date 2026-06-22 --end-date 2026-06-23`.
2. User will build 10 daily successful Cloud runs from `main` for
   `2026-06-14` through exclusive end `2026-06-24`; no local Cloud-trigger
   action is pending.
3. Monitor Cloud run `manual__2026-06-24T13:30:43+00:00` for the Scenario 1
   additive schema drift demo, then ask the Slack agent to inspect/explain the
   run and schema evolution behavior.
4. Ask the Slack agent to diagnose and fix Scenario 2 Cloud run
   `manual__2026-06-24T13:59:14+00:00`. The failed asset is
   `silver.salesforce_opportunity_pipeline`; the Cloud failed log reports
   Snowflake query `01c543cb-0000-60f3-0001-003e0006c732` and invalid identifier
   `AGENT_TEST_SCORE`.
5. Use Scenario 3 to ask the Slack agent why the `Average approved loan APR`
   KPI is low, then have it inspect and fix the metric label without changing
   the calculation unless evidence proves the SQL is wrong.
6. Review the new data activation and Salesforce admin skill under
   `.agents/data-activation-salesforce-admin/` before wiring it into a
   Bruin Slack agent. The next data-activation test should be a user-approved
   scoped dry-run for a real activation request; do not perform live writes
   until the dry-run summary is explicitly approved.
7. Confirm Salesforce storage capacity before running a full 2015 historical
   refresh, because the seed now generates every date in the interval.
8. Commit/push/deploy the local `gold.pipeline_by_channel_monthly`
   `create+replace` materialization fix.
9. Rerun `gold.pipeline_by_channel_monthly` first in Cloud, then rerun the full
   pipeline if the single-asset run passes.
10. Deploy `gold.pipeline_by_channel_daily` and run one Cloud `--full-refresh`
   bootstrap for that asset before normal interval runs if the target table is
   absent.
11. Keep the Salesforce Cloud connection on username/password/security-token auth
   now that SOAP API login is enabled; use access-token auth only as a temporary
   fallback.
12. Add operational runbook or agent context for:
   - Salesforce OAuth expiration;
   - Snowflake private key missing or rotated;
   - Salesforce storage-limit handling;
   - daily interval convention;
   This is now started in `.agents/self-healing/`; keep extending it as
   new Cloud failures are observed.
13. If Campaign attribution is important in a future demo, enable Campaign
   creation for the Salesforce user or pre-seed Campaign/CampaignMember rows,
   then replace the `bronze.salesforce_campaign_members` source-shaped SQL shim
   with an ingestr asset again.
   - rerun and verification commands.
14. Continue planned Snowflake cost-optimization agent work under
    `.agents/cost-optimizer/`.
