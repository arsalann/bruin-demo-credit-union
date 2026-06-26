# Credit Union Salesforce Demo Plan

## Goal

Build a credit union demo project that shows a Bruin-managed CRM analytics pipeline for a California credit union:

1. Generate realistic Salesforce demo data from `2015-01-01` forward while
   keeping daily runs interval-scoped and storage-safe.
2. Ingest Salesforce objects into a warehouse with Bruin ingestr assets.
3. Model bronze Salesforce data into governed silver and gold tables.
4. Prepare Bruin Cloud agent skills and context for self-healing and warehouse cost optimization.

## Current State

- Project migrated into the repository root.
- On 2026-06-26, the repo was refactored from a named-client demo to a generic
  credit union demo. Tracked paths, pipeline names, docs, seed data prefixes,
  environment variables, scenario custom fields, and agent context now use
  `credit-union`, `credit_union_dwh`, `CREDIT_UNION_*`, `CREDIT-UNION-DEMO`,
  and `Credit_Union_Agent_Test_*` naming.
- The BigQuery starter pipeline was used as the prototype and migration
  baseline, then retired after the Snowflake pipeline ran end to end.
- The BigQuery pipeline folder `pipelines/salesforce_bigquery_demo/` has
  been deleted to keep Snowflake as the primary demo path.
- The Snowflake connection
  `snowflake-default` is present in `.bruin.yml`; the local connection now points
  to database `CREDIT_UNION_DEMO`, schema `BRONZE`, warehouse `COMPUTE_WH`, and role
  `ACCOUNTADMIN`.
- Snowflake demo pipeline created at
  `pipelines/credit_union_dwh/`. The pipeline definition starts at
  `2015-01-01`. A local 2015 full-refresh run and a normal local daily run for
  `2026-06-22` to `2026-06-23` completed end to end with all assets and checks
  passing after the missing Snowflake key was restored.
- `bruin connections test --name snowflake-default` currently hangs without
  output and was manually stopped, but the same connection details work through
  a direct Snowflake connector probe.
- Bruin Cloud now uses the merged pipeline code at asset version
  `425cb4bedc51ffeb35478490b32e939e4ffb0b02`.
- Salesforce Cloud auth was repaired by enabling SOAP API login in Salesforce.
  The 2026-06-23 Cloud retry passed the seed asset, all four bronze Salesforce
  ingestr assets, both silver assets, and three of four gold assets.
- Current local fix: `gold.pipeline_by_channel_monthly` was changed from
  `delete+insert` to `create+replace` table materialization to avoid Bruin's
  unqualified Snowflake temp table path. The single-asset local run passed with
  all 6 checks. Next Cloud step is to deploy this change and rerun that asset.
- Added `gold.pipeline_by_channel_daily` as the Bruin `time_interval`
  materialization example. It uses `close_date` as the date-grain
  `incremental_key`; local bootstrap with `--full-refresh` and the subsequent
  normal interval run both passed.
- Expanded the Salesforce demo to a fuller CRM pipeline: Leads, Campaigns,
  Users, Products, Pricebooks, PricebookEntries, OpportunityContactRoles,
  OpportunityLineItems, and Events are now represented in bronze. Product,
  marketing, activity, branch health, and banker coverage models were added in
  silver/gold. A normal full-pipeline daily run for `2026-06-23` to
  `2026-06-24` passed all 29 assets and 138 checks in 33.31s.

## Target Structure

```text
PLAN.md
handoff.md
pipelines/
  credit_union_dwh/
    pipeline.yml
    README.md
    assets/
.agents/
  self-healing/
  data-activation-salesforce-admin/
  cost-optimizer/
notes/
scratch/
```

## Phase 1: Salesforce Demo Data and BigQuery Prototype

Status: complete and retired. The BigQuery prototype proved the Salesforce
source, seed behavior, and bronze/silver/gold model shape. It was deleted after
the Snowflake pipeline ran end to end.

Objective: prove the Salesforce source, deterministic seed generator, and
bronze/silver/gold model shape before promoting the active path to Snowflake.

### Data generation requirements

- Use Bruin Python assets without Python materialization. Completed in
  `bronze.seed_salesforce_demo_data`; it writes to Salesforce and logs
  counts, but does not return a warehouse materialization.
- Use Bruin interval environment variables:
  - `BRUIN_START_DATE`
  - `BRUIN_END_DATE`
  - `BRUIN_START_DATETIME`
  - `BRUIN_END_DATETIME`
- Generate deterministic Salesforce records for any requested interval so the pipeline can be backfilled or rerun safely.
- Generate data beginning `2015-01-01`; support interval windows through current demo execution dates.
- Use Salesforce-native IDs and upsert behavior where possible to avoid duplicate demo data on reruns.
- Keep credentials in `.bruin.yml` or ignored local credential paths only; do not commit secrets.
- The seed interval controls synthetic business dates. Salesforce
  `SystemModstamp` is still the real Salesforce write timestamp, so the first
  bronze ingestion after seeding should use `--full-refresh` or a current
  `SystemModstamp` interval rather than a historical business-date interval.

### Credit union-specific sample data theme

Use credit union CRM scenarios that feel realistic for a California member-owned financial institution:

- Accounts:
  - Member households, small businesses, nonprofit/community organizations, and indirect dealer partners.
  - California geographies such as San Francisco Bay Area, Sacramento, Central Valley, Los Angeles, San Diego, and nearby branch markets.
  - Account attributes for membership tenure, preferred branch, digital engagement tier, household deposits, and relationship segment.
- Contacts:
  - Primary members, joint owners, business principals, trustees, and authorized users.
  - Communication preferences, branch affiliation, language preference, and member lifecycle stage.
- Leads and campaigns:
  - Prospective members from web, branch, community event, partner, and phone channels.
  - Outreach themes for auto refinance, first-time homebuyer, financial wellness, cards, small business, and CD renewals.
  - CampaignMember rows are modeled, but current Salesforce org permissions prevent new Campaign/CampaignMember seed writes.
- Opportunities:
  - Auto loans, credit cards, HELOCs, mortgages, personal loans, checking, savings, CDs, business banking, and financial wellness referrals.
  - Stages such as Prospecting, Needs Analysis, Application Started, Underwriting, Approved, Funded/Closed Won, and Closed Lost.
  - Amounts and probabilities that match financial-product behavior.
  - Close dates distributed across the requested interval with realistic seasonality.
- Products, tasks, and events:
  - Salesforce product catalog and price book entries for product-grain pipeline reporting.
  - Banker follow-ups, document collection, underwriting callbacks, appointment reminders, financial wellness outreach, member onboarding, and cross-sell activities.
  - Completed and open tasks tied to opportunity stage and close-date timing.
  - Appointment events tied to opportunities and contacts for branch/video meeting coverage.

### Phase 1 tasks

- [x] Read and refactor the seed asset that is now active at
  `pipelines/credit_union_dwh/assets/bronze/seed_salesforce_demo_data.py`.
- [x] Confirm dependency handling in `requirements.txt`; dependencies are local to the asset folder and pandas was removed because the asset no longer materializes a DataFrame.
- [x] Ensure the seed asset:
  - reads the Bruin interval environment variables,
  - creates data only for the interval,
  - is deterministic and idempotent,
  - produces enough volume for demos,
  - logs counts by Salesforce object,
  - avoids Bruin Python table materialization.
- [x] Inspect bronze ingestr assets:
  - `salesforce_accounts.asset.yml`
  - `salesforce_contacts.asset.yml`
  - `salesforce_leads.asset.yml`
  - `salesforce_campaigns.asset.yml`
  - `salesforce_users.asset.yml`
  - `salesforce_products.asset.yml`
  - `salesforce_pricebooks.asset.yml`
  - `salesforce_pricebook_entries.asset.yml`
  - `salesforce_opportunities.asset.yml`
  - `salesforce_opportunity_contact_roles.asset.yml`
  - `salesforce_opportunity_line_items.asset.yml`
  - `salesforce_tasks.asset.yml`
  - `salesforce_events.asset.yml`
- [x] Verify each ingestr asset has the correct:
  - `type: ingestr`
  - Salesforce source connection
  - source table
  - destination configuration
  - incremental strategy
  - incremental key
  - primary keys
  - schema enforcement where appropriate
- [x] Update `README.md` paths and commands for the new client-folder structure.
- [x] Run:
  - Bruin validation for the prototype pipeline
  - seed asset for a narrow test interval
  - dry-run seed asset for a narrow test interval
- [x] Run individual Salesforce ingestr assets.
- [x] Run downstream silver/gold assets.
- [x] Verify destination row counts, sample rows, and min/max dates after ingestion.
- [x] Record every run command, status, row counts, blockers, and verification notes in this plan.

### Phase 1 validation commands

Retired with the deleted BigQuery pipeline. Use the Snowflake pipeline commands
under Phase 2 for active validation and runs.

## Phase 2: Salesforce to Snowflake Bronze Layer

Status: complete for the demo path. The Snowflake pipeline ran end to end for
`2026-01-01` through `2026-06-18` and was verified with direct Snowflake row
counts and modeled metrics.

Objective: maintain the active Credit Union DWH pipeline with a Snowflake bronze
layer loaded from Salesforce and silver/gold CRM analytics models.

### Phase 2 tasks

- [x] Create `pipelines/credit_union_dwh/` using the prototype pipeline as the baseline.
- [x] Update `pipeline.yml`:
  - set Snowflake as the default destination connection,
  - set `start_date: "2015-01-01"`,
  - use daily schedule semantics.
- [x] Create Snowflake bronze schemas/tables for Salesforce objects.
- [x] Configure ingestr assets with:
  - `destination: snowflake`
  - Salesforce `source_connection`
  - `incremental_strategy: merge`
  - Salesforce incremental key, expected to be `systemmodstamp` or the connector-supported timestamp field after verification
  - primary key `id`
  - schema enforcement where stable enough for the demo
- [x] Use one-time historical run from `2026-01-01` with `--full-refresh` after confirming full-refresh restrictions and expected destructive behavior.
- [x] Configure subsequent daily runs using interval-driven incremental extraction.
- [x] Update the pipeline for `2015-01-01` start-date semantics, storage-safe
  long full-refresh seed cadence, and incremental silver/gold materializations.
- [x] Restore the missing local Snowflake private key and rerun validation plus
  the requested `2015-01-01` full refresh.
- [x] Validate and run one asset at a time during migration.
- [x] Verify Snowflake row counts, min/max date coverage, sample records, and modeled metrics after the end-to-end run.

### Phase 2 run commands

```bash
bruin validate --fast pipelines/credit_union_dwh

CREDIT_UNION_ACCOUNTS_PER_DAY=1 \
CREDIT_UNION_CONTACTS_PER_ACCOUNT=1 \
CREDIT_UNION_OPPORTUNITIES_PER_ACCOUNT=1 \
CREDIT_UNION_TASKS_PER_OPPORTUNITY=1 \
CREDIT_UNION_LEADS_PER_DAY=1 \
CREDIT_UNION_EVENTS_PER_OPPORTUNITY=1 \
bruin run --full-refresh --start-date 2015-01-01 --end-date 2026-06-23 \
  pipelines/credit_union_dwh
```

### Phase 2 connection status

- Bruin connection name: `snowflake-default`
- Database: `CREDIT_UNION_DEMO`
- Schema: `BRONZE`
- Warehouse: `COMPUTE_WH`
- Role: `ACCOUNTADMIN`
- Auth: private key path in `.bruin.yml`; key file exists and is readable.
- Direct probe result:
  - `current_database`: `CREDIT_UNION_DEMO`
  - `current_schema`: `BRONZE`
  - `current_warehouse`: `COMPUTE_WH`
  - `current_role`: `ACCOUNTADMIN`
- Caveat: `bruin connections test --name snowflake-default` has hung silently
  twice and was killed manually. Use `bruin validate` and one-asset Snowflake
  runs as the practical verification path unless the Bruin connection-test
  behavior changes.

## Phase 3: Silver and Gold Modeling

Status: expanded and locally verified.

Objective: build governed Snowflake SQL assets that transform Salesforce bronze data into analytics-ready silver and gold layers.

### Silver layer candidates

- `silver.salesforce_account_health`
- `silver.salesforce_opportunity_pipeline`
- `silver.salesforce_product_pipeline`
- `silver.salesforce_marketing_funnel`
- `silver.salesforce_activity_timeline`

### Gold layer candidates

- `gold.pipeline_kpis`
- `gold.pipeline_by_stage`
- `gold.pipeline_by_channel_daily`
- `gold.pipeline_by_channel_monthly`
- `gold.activity_coverage_by_product`
- `gold.product_pipeline_performance`
- `gold.campaign_conversion_funnel`
- `gold.branch_relationship_health`
- `gold.banker_activity_coverage`

### Governance requirements

- Add extensive table descriptions in each asset definition.
- Add column-level descriptions for all modeled fields.
- Add owners, tags, domains, data sensitivity, refresh cadence, SLA expectations, and business glossary references through `meta`, `tags`, and related Bruin asset metadata fields.
- Include checks for primary keys, non-null business keys, accepted values, and important metric sanity thresholds.
- Add pipeline-level `README.md` documenting:
  - source object meaning,
  - transformation rules,
  - stage mapping,
  - product-family mapping,
  - credit union business logic,
  - expected run cadence,
  - operational verification steps.

### Phase 3 latest run log

On 2026-06-23, the expanded pipeline was validated and run end to end.

- `python3 -m py_compile pipelines/credit_union_dwh/assets/bronze/seed_salesforce_demo_data.py`: passed.
- `bruin format pipelines/credit_union_dwh`: passed for 29 assets.
- `bruin validate --fast pipelines/credit_union_dwh`: passed for 29 assets.
- Seed dry-run for `2026-06-22` to `2026-06-23`: passed; planned 1 Account,
  Contact, Lead, Opportunity, OpportunityContactRole, OpportunityLineItem, Task,
  Event, 1 monthly Campaign, and 9 Products/PricebookEntries.
- An attempted `--full-refresh` pipeline run was stopped because Bruin expanded
  the interval to pipeline start `2015-01-01`, which would have seeded 4,191
  rows per interval object. The run was killed before any object-level seed
  write summary was emitted; only `bronze.salesforce_users` completed.
- Daily seed for `2026-06-22` to `2026-06-23`: passed after making Campaign
  seeding capability-aware. Salesforce reports Campaign is not createable for
  this user, so new Campaign/CampaignMember rows are skipped.
- Bronze full-refresh source loads were run one asset at a time to create and
  refresh the new Snowflake tables. `bronze.salesforce_campaign_members` was
  changed to a source-shaped empty SQL table because ingestr fails on empty
  CampaignMember extracts in this org.
- Full silver/gold rebuilds passed one asset at a time.
- Normal full-pipeline run command:
  `CREDIT_UNION_ACCOUNTS_PER_DAY=1 CREDIT_UNION_CONTACTS_PER_ACCOUNT=1 CREDIT_UNION_OPPORTUNITIES_PER_ACCOUNT=1 CREDIT_UNION_TASKS_PER_OPPORTUNITY=1 CREDIT_UNION_LEADS_PER_DAY=1 CREDIT_UNION_EVENTS_PER_OPPORTUNITY=1 bruin run --start-date 2026-06-23 --end-date 2026-06-24 pipelines/credit_union_dwh`.
- Result: 29 assets succeeded, 138 quality checks succeeded, runtime 33.31s.
- Verified row counts: bronze Accounts 590, Contacts 478, Leads 24, Campaigns
  4, CampaignMembers 0, Users 8, Products 26, Pricebooks 2, PricebookEntries
  43, Opportunities 502, OpportunityContactRoles 2, OpportunityLineItems 2,
  Tasks 471, Events 2; silver AccountHealth 590, OpportunityPipeline 502,
  ProductPipeline 2, MarketingFunnel 0, ActivityTimeline 473; gold
  ActivityCoverageByProduct 6, BankerActivityCoverage 1,
  BranchRelationshipHealth 20, CampaignConversionFunnel 0,
  PipelineByChannelDaily 281, PipelineByChannelMonthly 167, PipelineByStage 5,
  PipelineKPIs 4, ProductPipelinePerformance 2.

## Phase 4: Bruin Cloud Agent Skills and Context

Status: in progress. Self-healing and data-activation Salesforce admin agent
context now exists under `.agents/`; Snowflake cost optimization is
still planned.

Objective: prepare project-specific skills and context so Bruin Cloud agents can support self-healing and cost optimization for the Credit Union Salesforce-to-Snowflake pipeline.

### Source materials

- Self-healing skills source:
  `/Users/bear/Github/data_playground/.agents`
- BigQuery cost optimizer source:
  `/Users/bear/Github/bruin-common/.agents/skills/cost-explorer-bigquery/SKILL.md`

### Target materials

- `.agents/self-healing/`
- `.agents/data-activation-salesforce-admin/`
- `.agents/cost-optimizer/`

### Self-healing agent customization

- Tailor the copied skills to:
  - Salesforce source diagnostics,
  - Snowflake destination diagnostics,
  - Bruin ingestr run failures,
  - Salesforce auth/token failures,
  - schema drift on Salesforce standard objects,
  - incremental-key gaps,
  - missing daily partitions/intervals,
  - downstream silver/gold model failures.
- Include project-specific runbooks for:
  - validating connections,
  - reading Bruin Cloud run logs,
  - rerunning one failed asset,
  - verifying downstream recovery,
  - documenting incidents in `HANDOFF.md` or the active plan.

### Cost optimizer customization

- Convert the BigQuery-focused cost explorer skill into a Snowflake-focused credit union skill.
- Focus on:
  - Snowflake query history,
  - warehouse credit consumption,
  - asset-level query tags from Bruin,
  - long-running model queries,
  - oversized warehouses,
  - inefficient incremental predicates,
  - opportunities for clustering, pruning, materialization changes, or schedule changes.
- Include recommended read-only connection-set permissions for a Bruin Cloud cost optimization agent.

### Data activation and Salesforce admin customization

- Added `.agents/data-activation-salesforce-admin/` for a Bruin Slack
  agent that can activate approved warehouse or user-provided data into
  Salesforce and perform scoped Salesforce admin changes.
- Reused the Salesforce credential pattern from
  `pipelines/credit_union_dwh/assets/bronze/seed_salesforce_demo_data.py`:
  Bruin injects the `salesforce` connection as `SALESFORCE_CONNECTION`, and the
  helper builds a `simple_salesforce.Salesforce` client without exposing
  secrets.
- The skill requires dry-run summaries, explicit approval gates for risky
  writes, object/field/match-key scoping, chunked record writes, post-write
  Salesforce verification, and downstream Bruin verification when warehouse
  models should reflect the activation.

## Run Log

| Date | Phase | Command | Status | Notes |
|---|---:|---|---|---|
| 2026-06-19 | Setup | Copied starter pipeline into `pipelines/salesforce_bigquery_demo/` | Done | Source was existing Salesforce-to-BigQuery demo pipeline. |
| 2026-06-19 | Setup | `bruin validate pipelines/salesforce_bigquery_demo` | Passed | Validated 11 assets across 1 pipeline with no issues. |
| 2026-06-19 | Phase 1 | Refactored `seed_salesforce_demo_data.py` | Done | Converted to no-materialization Bruin Python asset; uses interval dates, deterministic per-day records, standard Salesforce fields, and structured object count logs. |
| 2026-06-19 | Phase 1 | Updated `assets/bronze/requirements.txt` | Done | Removed `pandas`; kept `requests` and `simple-salesforce`. |
| 2026-06-19 | Phase 1 | `CREDIT_UNION_DRY_RUN=1 CREDIT_UNION_ACCOUNTS_PER_DAY=2 bruin run --start-date 2026-01-01 --end-date 2026-01-02 pipelines/salesforce_bigquery_demo/assets/bronze/seed_salesforce_demo_data.py` | Passed | Generated plan for 4 accounts, 8 contacts, 12 opportunities, and 24 tasks; skipped Salesforce writes. |
| 2026-06-19 | Phase 1 | `bruin format pipelines/salesforce_bigquery_demo` | Passed | Formatted 11 assets. |
| 2026-06-19 | Phase 1 | `bruin validate pipelines/salesforce_bigquery_demo` | Passed | Validated 11 assets across 1 pipeline with no issues after edits. |
| 2026-06-19 | Phase 1 | `python3 -m py_compile pipelines/salesforce_bigquery_demo/assets/bronze/seed_salesforce_demo_data.py` | Passed | Direct Python compile check passed. |
| 2026-06-19 | Phase 1 | `bruin connections test --name bruin-playground-arsalan` | Passed | BigQuery destination connection tested successfully. |
| 2026-06-19 | Phase 1 | `bruin connections test --name salesforce` | Not supported | Bruin reported that this Salesforce connection type does not support `connections test` yet. |
| 2026-06-19 | Phase 1 | `CREDIT_UNION_ACCOUNTS_PER_DAY=1 CREDIT_UNION_CONTACTS_PER_ACCOUNT=1 CREDIT_UNION_OPPORTUNITIES_PER_ACCOUNT=1 CREDIT_UNION_TASKS_PER_OPPORTUNITY=1 bruin run --start-date 2026-01-01 --end-date 2026-01-01 pipelines/salesforce_bigquery_demo/assets/bronze/seed_salesforce_demo_data.py` | Blocked | Salesforce returned `INVALID_SESSION_ID` on the first SOQL query. Both configured Salesforce OAuth access-token connections also returned `INVALID_SESSION_ID` for a direct SOQL probe. Refresh `.bruin.yml` Salesforce token before live seed/ingestion. |
| 2026-06-19 | Phase 1 | `sf org auth show-access-token --target-org credit-union-salesforce --json` piped into `.bruin.yml` updater | Done | Replaced redacted CLI display placeholder with a real 112-character OAuth token without printing the token. Direct SOQL probe against the `salesforce` Bruin connection returned HTTP 200. |
| 2026-06-19 | Phase 1 | `CREDIT_UNION_ACCOUNTS_PER_DAY=1 CREDIT_UNION_CONTACTS_PER_ACCOUNT=1 CREDIT_UNION_OPPORTUNITIES_PER_ACCOUNT=1 CREDIT_UNION_TASKS_PER_OPPORTUNITY=1 bruin run --start-date 2026-01-01 --end-date 2026-01-01 pipelines/salesforce_bigquery_demo/assets/bronze/seed_salesforce_demo_data.py` | Passed | Live seed smoke test succeeded: 1 account updated, 1 contact created, 1 opportunity updated, 1 task updated; 0 errors. |
| 2026-06-19 | Phase 1 | Salesforce source count inspection after smoke test | Passed | Demo source counts before historical seed: 6 Accounts, 11 Contacts, 11 Opportunities, 11 Tasks. |
| 2026-06-19 | Phase 1 | `CREDIT_UNION_ACCOUNTS_PER_DAY=5 CREDIT_UNION_CONTACTS_PER_ACCOUNT=2 CREDIT_UNION_OPPORTUNITIES_PER_ACCOUNT=3 CREDIT_UNION_TASKS_PER_OPPORTUNITY=2 bruin run --start-date 2026-01-01 --end-date 2026-06-18 pipelines/salesforce_bigquery_demo/assets/bronze/seed_salesforce_demo_data.py` | Blocked | Accounts completed: 845 generated, 844 created, 1 updated, 0 errors. Contacts completed: 1,690 generated, 1,689 created, 1 updated, 0 errors. Opportunity creation then hit Salesforce `STORAGE_LIMIT_EXCEEDED`; run was terminated after repeated storage errors. |
| 2026-06-19 | Phase 1 | Salesforce source count inspection after terminated historical seed | Partial | Current demo source counts: 850 Accounts, 1,700 Contacts, 228 Opportunities, 11 Tasks. |
| 2026-06-19 | Phase 1 | Updated `seed_salesforce_demo_data.py` storage-limit handling | Done | Added fail-fast handling for `STORAGE_LIMIT_EXCEEDED` so future runs stop immediately with an actionable message. |
| 2026-06-19 | Phase 1 | Deleted synthetic Salesforce records in child-to-parent order | Passed | Deleted 11 Tasks, 228 Opportunities, 1,700 Contacts, and 850 Accounts; 0 deletion errors. Verified all four synthetic object counts were 0 before reseed. |
| 2026-06-19 | Phase 1 | `CREDIT_UNION_ACCOUNTS_PER_DAY=1 CREDIT_UNION_CONTACTS_PER_ACCOUNT=1 CREDIT_UNION_OPPORTUNITIES_PER_ACCOUNT=1 CREDIT_UNION_TASKS_PER_OPPORTUNITY=1 bruin run --start-date 2026-01-01 --end-date 2026-06-18 pipelines/salesforce_bigquery_demo/assets/bronze/seed_salesforce_demo_data.py` | Passed | Reseeded storage-safe historical demo data: 169 Accounts, 169 Contacts, 169 Opportunities, and 169 Tasks created; 0 errors; duration 4m47s. |
| 2026-06-19 | Phase 1 | Salesforce source verification after reseed | Passed | Counts: 169 demo Accounts, 169 demo Contacts, 169 demo Opportunities, 169 demo Tasks. Opportunity close dates span 2026-01-12 to 2026-08-02. Task activity dates span 2026-01-01 to 2026-06-18. |
| 2026-06-19 | Phase 1 | `bruin run --full-refresh .../salesforce_accounts.asset.yml` | Passed | Loaded 182 Account rows into BigQuery, including 169 demo rows. |
| 2026-06-19 | Phase 1 | `bruin run --full-refresh .../salesforce_contacts.asset.yml` | Passed | Loaded 189 Contact rows into BigQuery, including 169 demo rows. |
| 2026-06-19 | Phase 1 | `bruin run --full-refresh .../salesforce_opportunities.asset.yml` | Passed | Loaded 200 Opportunity rows into BigQuery, including 169 demo rows. |
| 2026-06-19 | Phase 1 | `bruin run --full-refresh .../salesforce_tasks.asset.yml` | Passed | Loaded 169 Task rows into BigQuery, all demo rows. |
| 2026-06-19 | Phase 1 | BigQuery bronze verification queries | Passed | Bronze demo counts matched Salesforce source: 169 demo rows in each bronze object. Account/Contact/Opportunity include existing non-demo Salesforce rows because the ingestr assets ingest full standard objects. |
| 2026-06-19 | Phase 1 | Built silver assets | Passed | `salesforce_opportunity_pipeline` has 200 rows; `salesforce_account_health` has 182 rows. |
| 2026-06-19 | Phase 1 | Built gold assets | Passed | `pipeline_kpis`: 4 rows; `pipeline_by_stage`: 5 rows; `pipeline_by_channel_monthly`: 49 rows; `activity_coverage_by_product`: 6 rows. |
| 2026-06-19 | Phase 1 | Final modeled metric verification | Passed | Opportunity pipeline has 200 rows, 169 demo opportunities, close dates 2026-01-12 to 2026-08-02, total amount USD about 29.23M, weighted amount USD about 19.29M, and 169 linked activities. |
| 2026-06-22 | Phase 2 | `bruin connections test --name snowflake-default` | Hung | Command produced no output after roughly 90 seconds and was killed. |
| 2026-06-22 | Phase 2 | Direct Snowflake connector probe using `.bruin.yml` settings | Passed | Connected with database `USER$ARSALAN`, schema `CREDIT_UNION_RAW`, warehouse `COMPUTE_WH`, and role `ACCOUNTADMIN`. |
| 2026-06-22 | BigQuery refactor | Renamed BigQuery assets and folders from legacy raw, staging, and reports datasets to `bronze`, `silver`, and `gold` | Done | Updated Bruin asset names, dependencies, SQL references, README commands, plan, and handoff. |
| 2026-06-22 | BigQuery refactor | `bruin format pipelines/salesforce_bigquery_demo` | Passed | Formatted 11 assets after the dataset rename. |
| 2026-06-22 | BigQuery refactor | `python3 -m py_compile pipelines/salesforce_bigquery_demo/assets/bronze/seed_salesforce_demo_data.py` | Passed | Seed asset still compiles after folder and asset-name rename. |
| 2026-06-22 | BigQuery refactor | `bruin validate pipelines/salesforce_bigquery_demo` | Blocked | Full validation initially failed because the new BigQuery datasets/tables did not exist yet. |
| 2026-06-22 | BigQuery refactor | `bruin query --connection bruin-playground-arsalan --description "create bronze silver gold BigQuery datasets for credit union dataset-name refactor" ...` | Passed | Created BigQuery datasets `bronze`, `silver`, and `gold` in location `US`. |
| 2026-06-22 | BigQuery refactor | `bruin run --full-refresh pipelines/salesforce_bigquery_demo/assets/bronze/salesforce_accounts.asset.yml` | Blocked then passed | First attempt failed with Salesforce `INVALID_SESSION_ID`; refreshed local `.bruin.yml` from `sf org auth show-access-token --target-org credit-union-salesforce --json` without printing the token, then reloaded 182 Account rows into `bronze.salesforce_accounts`. |
| 2026-06-22 | BigQuery refactor | `bruin run --full-refresh .../assets/bronze/salesforce_contacts.asset.yml` | Passed | Loaded 189 Contact rows into `bronze.salesforce_contacts`. |
| 2026-06-22 | BigQuery refactor | `bruin run --full-refresh .../assets/bronze/salesforce_opportunities.asset.yml` | Passed | Loaded 200 Opportunity rows into `bronze.salesforce_opportunities`. |
| 2026-06-22 | BigQuery refactor | `bruin run --full-refresh .../assets/bronze/salesforce_tasks.asset.yml` | Passed | Loaded 169 Task rows into `bronze.salesforce_tasks`. |
| 2026-06-22 | BigQuery refactor | Built silver assets with Bruin | Passed | `silver.salesforce_opportunity_pipeline` has 200 rows; `silver.salesforce_account_health` has 182 rows. |
| 2026-06-22 | BigQuery refactor | Built gold assets with Bruin | Passed | `gold.pipeline_kpis`: 4 rows; `gold.pipeline_by_stage`: 5 rows; `gold.pipeline_by_channel_monthly`: 49 rows; `gold.activity_coverage_by_product`: 6 rows. |
| 2026-06-22 | BigQuery refactor | `bruin validate pipelines/salesforce_bigquery_demo` | Passed | Final validation passed for all 11 assets after rebuilding the renamed datasets. |
| 2026-06-22 | BigQuery refactor | BigQuery verification queries for renamed datasets | Passed | Row counts: bronze Accounts 182, Contacts 189, Opportunities 200, Tasks 169; silver Account Health 182 and Opportunity Pipeline 200; gold KPI 4, Stage 5, Monthly Channel 49, Activity Coverage 6. Opportunity close dates span 2026-01-12 to 2026-08-02, total amount is about 29.23M USD, weighted amount about 19.29M USD, and linked activities total 169. |
| 2026-06-22 | Phase 2 | Created `pipelines/credit_union_dwh/` from the BigQuery baseline | Done | Converted pipeline default connection to `snowflake-default`, bronze ingestr destinations to `snowflake`, SQL asset types to `sf.sql`, and BigQuery SQL functions to Snowflake syntax. |
| 2026-06-22 | Phase 2 | Added `bronze.seed_salesforce_demo_data` as an upstream dependency for each Snowflake bronze ingestr asset | Done | Updated Account, Contact, Opportunity, and Task ingestr assets so lineage records the Salesforce seed step upstream of ingestion. |
| 2026-06-22 | Phase 2 | `bruin format pipelines/credit_union_dwh` | Passed | Formatted 11 Snowflake pipeline assets. |
| 2026-06-22 | Phase 2 | `python3 -m py_compile pipelines/credit_union_dwh/assets/bronze/seed_salesforce_demo_data.py` | Passed | Seed asset compiles in the Snowflake pipeline folder. |
| 2026-06-22 | Phase 2 | `bruin validate --fast pipelines/credit_union_dwh` | Passed | Fast validation passed for all 11 assets. Full Snowflake validation hung before emitting results, consistent with earlier Snowflake CLI behavior. |
| 2026-06-22 | Phase 2 | `bruin run --full-refresh pipelines/credit_union_dwh/assets/bronze/salesforce_accounts.asset.yml` | Blocked | First attempt reached Salesforce and Snowflake but failed because `.bruin.yml` pointed `snowflake-default` at personal database `USER$ARSALAN`; Snowflake rejected table creation with `Tables cannot currently be created in a personal database`. |
| 2026-06-22 | Phase 2 | Created Snowflake database/schemas using direct connector | Passed | Created `CREDIT_UNION_DEMO` plus `BRONZE`, `SILVER`, `GOLD`, and `_BRUIN_STAGING` schemas. Updated local `.bruin.yml` so `snowflake-default` uses database `CREDIT_UNION_DEMO` and schema `BRONZE`. |
| 2026-06-22 | Phase 2 | `bruin run --full-refresh pipelines/credit_union_dwh/assets/bronze/salesforce_accounts.asset.yml` | Passed | Loaded 182 Account rows into `CREDIT_UNION_DEMO.BRONZE.SALESFORCE_ACCOUNTS`; direct Snowflake count verification returned 182 rows. |
| 2026-06-22 | Phase 2 | `CREDIT_UNION_ACCOUNTS_PER_DAY=1 CREDIT_UNION_CONTACTS_PER_ACCOUNT=1 CREDIT_UNION_OPPORTUNITIES_PER_ACCOUNT=1 CREDIT_UNION_TASKS_PER_OPPORTUNITY=1 bruin run --full-refresh --start-date 2026-01-01 --end-date 2026-06-18 pipelines/credit_union_dwh` | Partial | Seed passed with 169 updates and 0 errors for each Salesforce object. All four bronze ingestr assets passed: Accounts 182, Contacts 189, Opportunities 200, Tasks 169. Silver failed because Bruin's Snowflake connection used a regional hostname that failed TLS certificate verification. |
| 2026-06-22 | Phase 2 | Updated local `snowflake-default` connection | Done | Removed the `region` setting from `.bruin.yml`; Bruin's native Snowflake SQL runner then connected successfully using the account host directly. |
| 2026-06-22 | Phase 2 | `bruin run --continue --full-refresh --start-date 2026-01-01 --end-date 2026-06-18 pipelines/credit_union_dwh` | Failed then fixed | First continue reached Snowflake but failed because `TRY_CAST(number AS DOUBLE)` is invalid in Snowflake. Replaced those casts with normal Snowflake casts in the two silver SQL assets. |
| 2026-06-22 | Phase 2 | `bruin format pipelines/credit_union_dwh` and `bruin validate --fast pipelines/credit_union_dwh` | Passed | Formatted Snowflake assets and validated definitions after cast fixes. |
| 2026-06-22 | Phase 2 | `bruin run --continue --full-refresh --start-date 2026-01-01 --end-date 2026-06-18 pipelines/credit_union_dwh` | Passed | Silver and gold completed: `silver.salesforce_opportunity_pipeline`, `silver.salesforce_account_health`, `gold.activity_coverage_by_product`, `gold.pipeline_kpis`, `gold.pipeline_by_channel_monthly`, and `gold.pipeline_by_stage`. |
| 2026-06-22 | Phase 2 | Direct Snowflake row-count and metric verification | Passed | Counts: bronze Accounts 182, Contacts 189, Opportunities 200, Tasks 169; silver Account Health 182 and Opportunity Pipeline 200; gold KPI 4, Stage 5, Monthly Channel 49, Activity Coverage 6. Opportunity close dates span 2026-01-12 to 2026-08-02, total amount is 29,232,913.32 USD, weighted amount is 19,293,830.30 USD, and linked activities total 169. |
| 2026-06-22 | Cleanup | Deleted `pipelines/salesforce_bigquery_demo/` | Done | BigQuery prototype was safe to remove after Snowflake pipeline completed end to end and matched the known baseline counts. |
| 2026-06-22 | Cleanup | Renamed Snowflake pipeline folder and id to `credit_union_dwh` | Done | Moved `pipelines/salesforce_snowflake_demo/` to `pipelines/credit_union_dwh/` and changed `pipeline.yml` name from `credit-union_salesforce_snowflake_demo` to `credit_union_dwh`. |
| 2026-06-22 | Incremental optimization | Updated materialization and seed strategy for `2015-01-01` start | Done | Set `pipeline.yml` start date to `2015-01-01`; seed defaults to 1/1/1/1 object volume; bronze ingestr assets use schema enforcement, merge on `SystemModstamp`, and clustering; silver marts use `merge` by account/opportunity with interval-changed source rows; `gold.pipeline_by_channel_monthly` uses `delete+insert` by changed `close_month`; broad gold rollups are views. |
| 2026-06-22 | Metadata enhancement | `bruin ai enhance --codex --concurrency 1 pipelines/credit_union_dwh` | Stopped | The Codex provider spawned a nested Codex process and produced no progress after the initial first-asset prompt, so it was killed to avoid leaving a stuck process. |
| 2026-06-22 | Metadata enhancement | `bruin ai enhance --claude --concurrency 1 pipelines/credit_union_dwh` | Failed | Bruin selected `claude-sonnet-4-20250514`; local Claude CLI reported the model was unavailable or inaccessible. |
| 2026-06-22 | Metadata enhancement | `bruin ai enhance --claude --model claude-sonnet-4-5-20250929 --concurrency 1 pipelines/credit_union_dwh` | Blocked | Enhancement reached validation but stopped because `.credentials/credit-union/snowflake/rsa_key.p8` is missing. Manual tags, domains, meta, descriptions, and safe checks were added. |
| 2026-06-22 | Incremental optimization | `bruin format pipelines/credit_union_dwh` | Passed | Formatted all 11 assets after materialization and metadata updates. |
| 2026-06-22 | Incremental optimization | `python3 -m py_compile pipelines/credit_union_dwh/assets/bronze/seed_salesforce_demo_data.py` | Passed | Seed asset compiles after 2015 start-date changes. |
| 2026-06-22 | Incremental optimization | `bruin internal parse-asset` for all 11 assets | Passed | All edited Bruin asset definitions parse successfully without requiring live Snowflake. |
| 2026-06-22 | Incremental optimization | `bruin validate --fast pipelines/credit_union_dwh` | Blocked | Bruin failed while registering `snowflake-default`: missing `.credentials/credit-union/snowflake/rsa_key.p8`. |
| 2026-06-22 | Full refresh | `CREDIT_UNION_ACCOUNTS_PER_DAY=1 CREDIT_UNION_CONTACTS_PER_ACCOUNT=1 CREDIT_UNION_OPPORTUNITIES_PER_ACCOUNT=1 CREDIT_UNION_TASKS_PER_OPPORTUNITY=1 bruin run --full-refresh --start-date 2015-01-01 --end-date 2026-06-22 pipelines/credit_union_dwh` | Blocked | Run analyzed 11 assets but stopped before execution because `snowflake-default` could not load missing private key `.credentials/credit-union/snowflake/rsa_key.p8`. No Salesforce or Snowflake data changed. |
| 2026-06-22 | Credentials | Refreshed local Salesforce OAuth token from `sf org auth show-access-token --target-org credit-union-salesforce --json` | Done | Updated gitignored `.bruin.yml` without printing the token after the first 2015 full-refresh attempt failed with Salesforce `INVALID_SESSION_ID`. |
| 2026-06-22 | Incremental optimization | Removed invalid `incremental_key` fields from SQL `merge` materializations | Done | Bruin validation rejects `incremental_key` on SQL `merge`; interval pruning is implemented inside the silver SQL instead. `bruin validate --fast pipelines/credit_union_dwh` then passed. |
| 2026-06-22 | Full refresh | `CREDIT_UNION_ACCOUNTS_PER_DAY=1 CREDIT_UNION_CONTACTS_PER_ACCOUNT=1 CREDIT_UNION_OPPORTUNITIES_PER_ACCOUNT=1 CREDIT_UNION_TASKS_PER_OPPORTUNITY=1 bruin run --full-refresh --start-date 2015-01-01 --end-date 2026-06-22 pipelines/credit_union_dwh` | Passed | First successful 2015 full refresh completed in 9m40s under the previous sparse historical behavior: 11 assets succeeded and 72 checks passed. Seed generated 301 rows per object; initial run created many historical Salesforce records. |
| 2026-06-22 | Daily run verification | `CREDIT_UNION_ACCOUNTS_PER_DAY=1 CREDIT_UNION_CONTACTS_PER_ACCOUNT=1 CREDIT_UNION_OPPORTUNITIES_PER_ACCOUNT=1 CREDIT_UNION_TASKS_PER_OPPORTUNITY=1 bruin run --start-date 2026-06-22 --end-date 2026-06-22 pipelines/credit_union_dwh` | Failed then fixed | Seed generated one day but ingestr rejected zero-width interval because start and end were equal. Updated docs and seed interval handling to use Bruin `[start-date, end-date)` windows, e.g. `2026-06-22` to `2026-06-23`. |
| 2026-06-22 | Daily run verification | Fixed seed determinism for interval-independent contacts/opportunities/tasks | Done | Reworked the generator to use a global account index from `2015-01-01`, so daily reruns update the same Opportunity/Task generated by full refresh instead of creating alternate product rows. |
| 2026-06-22 | Cleanup | Deleted one duplicate June 22 Opportunity and Task created by the failed daily smoke test | Done | Removed the unintended Credit Card Balance Transfer June 22 Opportunity and related Task from Salesforce via API, without printing secrets. |
| 2026-06-22 | Daily run verification | `CREDIT_UNION_ACCOUNTS_PER_DAY=1 CREDIT_UNION_CONTACTS_PER_ACCOUNT=1 CREDIT_UNION_OPPORTUNITIES_PER_ACCOUNT=1 CREDIT_UNION_TASKS_PER_OPPORTUNITY=1 bruin run --start-date 2026-06-22 --end-date 2026-06-23 pipelines/credit_union_dwh` | Passed | Normal daily run completed in 18s: 11 assets succeeded, 72 checks passed, seed updated exactly 1 Account, 1 Contact, 1 Opportunity, and 1 Task with 0 creates and 0 errors. Bronze ingestr used `merge`. |
| 2026-06-22 | Full refresh | `CREDIT_UNION_ACCOUNTS_PER_DAY=1 CREDIT_UNION_CONTACTS_PER_ACCOUNT=1 CREDIT_UNION_OPPORTUNITIES_PER_ACCOUNT=1 CREDIT_UNION_TASKS_PER_OPPORTUNITY=1 bruin run --full-refresh --start-date 2015-01-01 --end-date 2026-06-23 pipelines/credit_union_dwh` | Passed | Clean rerun after duplicate cleanup completed in 7m41s under the previous sparse historical behavior: 11 assets succeeded and 72 checks passed. Seed updated 301 Accounts, Contacts, Opportunities, and Tasks; 0 creates and 0 errors. |
| 2026-06-22 | Seed change | Removed sparse historical generation limit from `bronze.seed_salesforce_demo_data` | Done | Full-refresh seed now generates every date in the requested Bruin interval. A 2015-01-01 to 2026-06-23 full refresh will plan roughly 4,191 generated days per object at 1/1/1/1 volume, so Salesforce storage must be available before running it live. |
| 2026-06-22 | Seed change verification | `CREDIT_UNION_DRY_RUN=1 CREDIT_UNION_ACCOUNTS_PER_DAY=1 CREDIT_UNION_CONTACTS_PER_ACCOUNT=1 CREDIT_UNION_OPPORTUNITIES_PER_ACCOUNT=1 CREDIT_UNION_TASKS_PER_OPPORTUNITY=1 bruin run --full-refresh --start-date 2015-01-01 --end-date 2026-06-23 pipelines/credit_union_dwh/assets/bronze/seed_salesforce_demo_data.py` | Passed | Dry run only; no Salesforce writes. Generation plan now shows 4,191 interval days and 4,191 Accounts, Contacts, Opportunities, and Tasks. |
| 2026-06-22 | Verification | Snowflake row count/date verification with `bruin query --connection snowflake-default --description "verify credit union clean full refresh row counts and date ranges after duplicate cleanup" ...` | Passed | Counts: bronze Accounts 470, Contacts 477, Opportunities 499, Tasks 468; silver Account Health 470 and Opportunity Pipeline 499; gold KPI 4, Stage 5, Monthly Channel 167, Activity Coverage 6. Generated demo keys span `CREDIT-UNION-DEMO-20150101-001` through `CREDIT-UNION-DEMO-20260622-001`; June 22 duplicate check returned exactly 1 Opportunity and 1 Task. |
| 2026-06-22 | Bruin Cloud troubleshooting | `bruin cloud projects list --output json`; `bruin cloud pipelines list --project-id <visible-project> --output json`; `bruin cloud runs list --project-id <visible-project> --pipeline credit_union_dwh --limit 1 --output json`; `bruin cloud runs diagnose --project-id <visible-project> --pipeline credit_union_dwh --latest` | Blocked | Bruin CLI authenticated via local `.bruin.yml` `bruin-cloud` token, but visible Cloud projects were `data_playground`, `bruin-community`, and `fifa2026`; none contained `credit_union_dwh`. Cloud returned `Pipeline not found`, so no credit union Cloud run or failed asset logs were available under this token. Local `bruin validate --fast pipelines/credit_union_dwh` passed. |
| 2026-06-22 | Local failure-log review | `sed -n '18,70p' logs/2026_06_22_17_30_52__credit_union_dwh.log` | Reviewed | Local failed run showed all four bronze ingestr assets failed because `--start-date 2026-06-22 --end-date 2026-06-22` produced a zero-width interval: `interval-start must be earlier than interval-end`. Follow-up run with exclusive end date `2026-06-23` passed. |
| 2026-06-22 | Current Snowflake verification | `bruin query --connection snowflake-default --description "verify credit union current Snowflake row counts after troubleshooting cloud visibility" --query ...` | Passed | Current counts match the last clean run: bronze Accounts 470, Contacts 477, Opportunities 499, Tasks 468; silver Account Health 470 and Opportunity Pipeline 499; gold KPI 4, Stage 5, Monthly Channel 167, Activity Coverage 6. |
| 2026-06-22 | Bruin Cloud troubleshooting | `bruin cloud runs diagnose --project-id 01kvqkcm7pg35gcggxwdrkx7hf --pipeline credit_union_dwh --latest`; `bruin cloud instances failed-logs --project-id 01kvqkcm7pg35gcggxwdrkx7hf --pipeline credit_union_dwh --run-id manual__2026-06-22T15:15:23+00:00` | Failed run inspected | Latest Cloud run `manual__2026-06-22T15:15:23+00:00` failed after 41s. Root failed asset is `bronze.seed_salesforce_demo_data`; all other assets were upstream_failed. Logs show Salesforce `INVALID_SESSION_ID` on the first Account SOQL query for 2026-06-21 demo keys. Cloud pipeline is also stale versus local: Cloud commit `146de563...` still starts at `2026-01-01` and seed defaults are 5/2/3/2, while local workspace starts at `2015-01-01` and defaults to 1/1/1/1 with sparse historical generation removed. |
| 2026-06-23 | Salesforce OAuth verification | `bruin run --start-date 2026-06-22 --end-date 2026-06-23 pipelines/credit_union_dwh/assets/bronze/salesforce_accounts.asset.yml` | Failed then passed | First run with `.bruin.yml` using `grant_type: client_credentials`, `client_id`, and `client_secret` failed inside Bruin ingestr with `username is required for Salesforce`; the Bruin Salesforce ingestr connector currently follows the documented `access_token` or username/password/security-token shapes. Minted an OAuth token from the client credentials without printing it, updated local `salesforce` to the Bruin-supported `access_token` shape, preserved the durable client credentials locally as `salesforce-client-credentials`, and reran the same asset successfully. Bruin fetched 457 Account rows from Salesforce, merged them into Snowflake, and all 6 quality checks passed in 14.9s. |
| 2026-06-23 | Salesforce username/password/token verification | `bruin run --start-date 2026-06-22 --end-date 2026-06-23 pipelines/credit_union_dwh/assets/bronze/salesforce_accounts.asset.yml` | Blocked by Salesforce org policy | Updated gitignored `.bruin.yml` to keep only one Salesforce connection named `salesforce` using username, password, security token, and domain. `bruin validate --fast pipelines/credit_union_dwh` passed, but the real Bruin ingestr run failed before data extraction because Salesforce returned `INVALID_OPERATION: SOAP API login() is disabled by default in this org. Contact the org administrator to enable SOAP API login().` The credentials shape is Bruin-documented, but this Salesforce org currently blocks SOAP login. |
| 2026-06-23 | Bruin Cloud latest run logs | `bruin cloud runs list --project-id 01kvqkcm7pg35gcggxwdrkx7hf --pipeline credit_union_dwh --limit 5 --output json`; `bruin cloud runs diagnose --project-id 01kvqkcm7pg35gcggxwdrkx7hf --pipeline credit_union_dwh --latest --output json`; `bruin cloud instances failed-logs --project-id 01kvqkcm7pg35gcggxwdrkx7hf --pipeline credit_union_dwh --run-id scheduled__2026-06-22T00:00:00+00:00` | Failed run inspected | Latest Cloud run `scheduled__2026-06-22T00:00:00+00:00` started 2026-06-23 11:58:48Z and failed after 51s. Root failed asset is `bronze.seed_salesforce_demo_data`; all other assets were `upstream_failed`. Logs show Cloud used Salesforce username/password/security-token login and failed with `SalesforceAuthenticationFailed: Authentication failed (code: INVALID_LOGIN): Invalid username, password, security token; or user locked out.` The run still uses Cloud asset version commit `146de563...`, which is stale versus local. |
| 2026-06-23 | Bruin Cloud retry after merge | `bruin cloud runs trigger --project-id 01kvqkcm7pg35gcggxwdrkx7hf --pipeline credit_union_dwh --start-date 2026-06-22T00:00:00Z --end-date 2026-06-23T00:00:00Z --var ...`; then clean retry without vars | Failed run inspected | First manual retry `manual__2026-06-23T12:22:34+00:00` failed because Cloud rejects undeclared variable overrides such as `CREDIT_UNION_ACCOUNTS_PER_DAY`. Clean retry `manual__2026-06-23T12:23:19+00:00` used merged asset version `425cb4bedc51ffeb35478490b32e939e4ffb0b02`, planned the expected 1/1/1/1 daily seed for 2026-06-22, and failed after 53s at `bronze.seed_salesforce_demo_data` with Salesforce `INVALID_LOGIN`. All downstream assets were `upstream_failed`. The code deploy is current; the remaining blocker is the Bruin Cloud `salesforce` connection/auth mode. |
| 2026-06-23 | Bruin Cloud single ingestion run | `bruin cloud instances failed-logs --project-id 01kvqkcm7pg35gcggxwdrkx7hf --pipeline credit_union_dwh --run-id manual__2026-06-23T12:29:04+00:00` | Failed run inspected | User-triggered `bronze.salesforce_accounts` run used merged asset version `425cb4bedc51ffeb35478490b32e939e4ffb0b02` and failed before extraction. Ingestr/simpleforce reported `failed to connect to source: failed to login to Salesforce` with `INVALID_OPERATION: SOAP API login() is disabled by default in this org.` This confirms the username/password/security-token Cloud connection path is blocked by Salesforce SOAP login policy. |
| 2026-06-23 | Bruin Cloud retry after SOAP enabled | `bruin cloud runs trigger --project-id 01kvqkcm7pg35gcggxwdrkx7hf --pipeline credit_union_dwh --start-date 2026-06-22T00:00:00Z --end-date 2026-06-23T00:00:00Z --note "Codex retry after enabling Salesforce SOAP API login"` | Failed late | Run `manual__2026-06-23T13:28:24+00:00` proved the Salesforce SOAP fix worked: `bronze.seed_salesforce_demo_data`, all four bronze Salesforce ingestr assets, both silver assets, and three gold assets succeeded. Final failure was only `gold.pipeline_by_channel_monthly`. Snowflake rejected Bruin's `delete+insert` temp table creation with `Cannot perform CREATE TEMPTABLE. This session does not have a current schema. Call 'USE SCHEMA', or use a qualified name.` This points to the Cloud `snowflake-default` connection missing a default schema/current schema for temp table materialization, or a Bruin delete+insert temp-table qualification issue. |
| 2026-06-23 | Fix Cloud gold failure locally | `bruin format pipelines/credit_union_dwh/assets/gold/pipeline_by_channel_monthly.sql`; `bruin validate --fast pipelines/credit_union_dwh`; `bruin run --start-date 2026-06-22 --end-date 2026-06-23 pipelines/credit_union_dwh/assets/gold/pipeline_by_channel_monthly.sql` | Passed | Changed `gold.pipeline_by_channel_monthly` from `delete+insert` to `create+replace` table materialization and removed the changed-month CTE so it rebuilds from the current silver opportunity mart. First attempt as a view failed locally because the existing target was a table. The final `create+replace` version passed locally in 2.8s with all 6 checks. |
| 2026-06-23 | Add time-interval gold asset | `bruin format pipelines/credit_union_dwh/assets/gold/pipeline_by_channel_daily.sql`; `bruin validate --fast pipelines/credit_union_dwh`; `bruin run --full-refresh --start-date 2026-06-22 --end-date 2026-06-23 pipelines/credit_union_dwh/assets/gold/pipeline_by_channel_daily.sql`; `bruin run --start-date 2026-06-22 --end-date 2026-06-23 pipelines/credit_union_dwh/assets/gold/pipeline_by_channel_daily.sql` | Passed | Added `gold.pipeline_by_channel_daily` with Bruin `time_interval` table materialization, `time_granularity: date`, and `incremental_key: close_date`. A first normal interval run failed because the target table did not exist, so the table was bootstrapped with `--full-refresh`; the following normal interval run passed with all 6 checks. Did not force `time_interval` onto the monthly asset because the monthly `close_month` grain does not align safely with daily run windows. |
| 2026-06-23 | Expanded Salesforce pipeline | `python3 -m py_compile pipelines/credit_union_dwh/assets/bronze/seed_salesforce_demo_data.py`; `bruin format pipelines/credit_union_dwh`; `bruin validate --fast pipelines/credit_union_dwh`; `CREDIT_UNION_ACCOUNTS_PER_DAY=1 CREDIT_UNION_CONTACTS_PER_ACCOUNT=1 CREDIT_UNION_OPPORTUNITIES_PER_ACCOUNT=1 CREDIT_UNION_TASKS_PER_OPPORTUNITY=1 CREDIT_UNION_LEADS_PER_DAY=1 CREDIT_UNION_EVENTS_PER_OPPORTUNITY=1 bruin run --start-date 2026-06-23 --end-date 2026-06-24 pipelines/credit_union_dwh`; row-count verification with `bruin query --connection snowflake-default --description "verify credit union expanded Salesforce demo row counts after end-to-end run" ...` | Passed | Added source coverage for Leads, Campaigns, Users, Products, Pricebooks, PricebookEntries, OpportunityContactRoles, OpportunityLineItems, and Events; added product, marketing, activity, branch health, and banker coverage models. End-to-end normal daily run passed 29 assets and 138 checks in 33.31s. Campaign creation is blocked in this Salesforce org, so CampaignMember is a source-shaped empty SQL table until rows are available. |
| 2026-06-23 | Dependency audit | `bruin lineage pipelines/credit_union_dwh/assets/silver/salesforce_activity_timeline.sql`; SQL-reference/`depends` comparison across all SQL assets; `bruin format pipelines/credit_union_dwh`; `bruin validate --fast pipelines/credit_union_dwh` | Passed | Removed the extra `bronze.salesforce_accounts` dependency from `silver.salesforce_activity_timeline`; the asset reads account IDs through `bronze.salesforce_opportunities`, not Accounts. Added `bronze.seed_salesforce_demo_data` upstream of `bronze.salesforce_users` so all Salesforce bronze extracts are gated by seed success for the demo. Final validation passed for 29 assets. `bronze.salesforce_campaign_members` keeps its semantic dependency on `bronze.salesforce_campaigns` because it is a source-shaped empty CampaignMember shim until CampaignMember rows are available. |
| 2026-06-23 | 2015 full-refresh backfill | `CREDIT_UNION_ACCOUNTS_PER_DAY=1 CREDIT_UNION_CONTACTS_PER_ACCOUNT=1 CREDIT_UNION_OPPORTUNITIES_PER_ACCOUNT=1 CREDIT_UNION_TASKS_PER_OPPORTUNITY=1 CREDIT_UNION_LEADS_PER_DAY=1 CREDIT_UNION_EVENTS_PER_OPPORTUNITY=1 bruin run --full-refresh --start-date 2015-01-01 --end-date 2026-06-24 pipelines/credit_union_dwh` | Failed at seed | Live Salesforce write backfill planned 4,192 generated days but failed after 5m15s with `STORAGE_LIMIT_EXCEEDED` while creating Account rows. Downstream assets were correctly skipped because all bronze Salesforce extracts now depend on seed success. |
| 2026-06-23 | 2015 full-refresh backfill fallback | `CREDIT_UNION_DRY_RUN=1 CREDIT_UNION_ACCOUNTS_PER_DAY=1 CREDIT_UNION_CONTACTS_PER_ACCOUNT=1 CREDIT_UNION_OPPORTUNITIES_PER_ACCOUNT=1 CREDIT_UNION_TASKS_PER_OPPORTUNITY=1 CREDIT_UNION_LEADS_PER_DAY=1 CREDIT_UNION_EVENTS_PER_OPPORTUNITY=1 bruin run --full-refresh --start-date 2015-01-01 --end-date 2026-06-24 pipelines/credit_union_dwh`; row/date verification queries with `bruin query --connection snowflake-default` | Passed | Seed ran in dry-run mode to avoid adding Salesforce storage, then all 29 assets and 138 quality checks passed in 1m14.921s. Snowflake full-refresh counts included bronze Accounts 1,373, Contacts 478, Leads 24, Opportunities 502, Tasks 471, Events 2, Users 8; silver AccountHealth 1,373, OpportunityPipeline 502, ActivityTimeline 473; gold KPI 4, Stage 5, Daily Channel 282, Monthly Channel 167, BranchRelationshipHealth 20. Demo Account keys span `CREDIT-UNION-DEMO-20150101-001` through `CREDIT-UNION-DEMO-20260623-001`; the live failed seed partially created additional Account rows before storage blocked Contact/Opportunity/Task expansion. |
| 2026-06-23 | 2025-09 full-refresh backfill | Temporarily set pipeline `start_date` to `2025-09-01` because Bruin full refresh uses the pipeline start date; `CREDIT_UNION_ACCOUNTS_PER_DAY=1 CREDIT_UNION_CONTACTS_PER_ACCOUNT=1 CREDIT_UNION_OPPORTUNITIES_PER_ACCOUNT=1 CREDIT_UNION_TASKS_PER_OPPORTUNITY=1 CREDIT_UNION_LEADS_PER_DAY=1 CREDIT_UNION_EVENTS_PER_OPPORTUNITY=1 bruin run --full-refresh --start-date 2025-09-01 --end-date 2026-06-24 pipelines/credit_union_dwh` | Failed at seed | Live Salesforce write backfill planned 296 generated days but failed in 1.898s with `STORAGE_LIMIT_EXCEEDED` while creating Account rows. No downstream assets ran. The pipeline `start_date` was restored to `2015-01-01` afterward. |
| 2026-06-23 | 2025-09 full-refresh backfill fallback | With temporary pipeline `start_date: 2025-09-01`, `CREDIT_UNION_DRY_RUN=1 CREDIT_UNION_ACCOUNTS_PER_DAY=1 CREDIT_UNION_CONTACTS_PER_ACCOUNT=1 CREDIT_UNION_OPPORTUNITIES_PER_ACCOUNT=1 CREDIT_UNION_TASKS_PER_OPPORTUNITY=1 CREDIT_UNION_LEADS_PER_DAY=1 CREDIT_UNION_EVENTS_PER_OPPORTUNITY=1 bruin run --full-refresh --start-date 2025-09-01 --end-date 2026-06-24 pipelines/credit_union_dwh`; then restored pipeline `start_date` and ran row-count verification | Passed | Dry-run seed avoided new Salesforce writes; all 29 assets and 138 checks passed in 29.393s. Verification counts after the run: bronze Accounts 1,373, Contacts 478, Leads 24, Opportunities 502, Tasks 471, Events 2; silver AccountHealth 1,373, OpportunityPipeline 502, ActivityTimeline 473; gold KPI 4, Stage 5, Daily Channel 282, Monthly Channel 167, BranchRelationshipHealth 20. This refresh rebuilt Snowflake from existing Salesforce data but did not create the missing 2025-09-to-2026-06 demo records because the Salesforce org has 0 MB remaining data storage. |
| 2026-06-23 | Salesforce demo reset | `.context/credit-union_salesforce_demo_reset.py` with `uv run --with simple-salesforce --with pyyaml`; then targeted stale pre-2026 Account delete | Passed with retry | Deleted namespaced credit union demo rows only, not all Salesforce org data. Initial cleanup removed Tasks 471, Events 2, OpportunityLineItems 2, OpportunityContactRoles 2, Opportunities 471, Contacts 458, Leads 2, Accounts 760 of 1,360, PricebookEntries 9, Products 9; storage improved from 5MB used/0MB free to 1MB used/4MB free. A follow-up targeted delete removed 429 stale pre-2026 Accounts in bulk and the remaining 29 individually. |
| 2026-06-23 | 2026 live full-refresh backfill | Temporarily set pipeline `start_date` to `2026-01-01`; `CREDIT_UNION_ACCOUNTS_PER_DAY=1 CREDIT_UNION_CONTACTS_PER_ACCOUNT=1 CREDIT_UNION_OPPORTUNITIES_PER_ACCOUNT=1 CREDIT_UNION_TASKS_PER_OPPORTUNITY=1 CREDIT_UNION_LEADS_PER_DAY=1 CREDIT_UNION_EVENTS_PER_OPPORTUNITY=1 bruin run --full-refresh --start-date 2026-01-01 --end-date 2026-06-24 pipelines/credit_union_dwh`; then dry-run seed full-refresh sync after stale Account cleanup and restored `start_date` to `2015-01-01` | Passed | Live seed generated 174 days, updated 171 Accounts, created 3 Accounts, 174 Contacts, 174 Leads, 174 Opportunities, 174 OpportunityContactRoles, 174 OpportunityLineItems, 174 Tasks, and 174 Events; Campaign creation still skipped by org permission. Full run passed 29 assets and 138 checks in 9m58.532s; follow-up dry-run seed sync passed 29 assets and 138 checks in 30.641s after stale Accounts were removed. Final demo rows span `2026-01-01` through `2026-06-23` with 174 Accounts, Contacts, Leads, Opportunities, Tasks, and Events each. Final Salesforce data storage: 2MB used, 3MB free of 5MB. |
| 2026-06-23 | Self-healing agent setup | Added `.agents/self-healing/` with Cloud agent prompt, skill/runbook, scenario README, and `scenarios/self_healing_scenarios.py` | Done | Agent prompt is optimized for Bruin Cloud run/log inspection, Snowflake read-only evidence, Salesforce schema drift, metric-definition fixes, and narrow Cloud reruns/retriggers. Scenario harness covers additive Opportunity attribute drift, string-format drift after an integer expectation, and an incorrect KPI metric label; Salesforce scenarios now include `--revert` cleanup with optional custom-field deletion so demos can be repeated. |
| 2026-06-23 | Self-healing agent verification | `python3 -m py_compile .agents/self-healing/scenarios/self_healing_scenarios.py`; `python3 .agents/self-healing/scenarios/self_healing_scenarios.py salesforce --help`; dry-run repo scenarios; `bruin validate --fast pipelines/credit_union_dwh` | Partial | Python compile passed, Salesforce scenario CLI help now shows `--revert` and `--delete-field`, and dry-run repo scenario commands reported the expected planned changes. Bruin validation was blocked before asset validation because `snowflake-default` references missing `.credentials/credit-union/snowflake/rsa_key.p8`; no secret value was printed. No Salesforce mutation was performed while adding the reset path. |
| 2026-06-23 | Self-healing agent full test | `python3 /Users/bear/.codex/skills/.system/skill-creator/scripts/quick_validate.py .agents/self-healing`; repo scenario apply/revert loops; Salesforce dry-run apply/revert with `uv run --with simple-salesforce --with pyyaml`; mocked Salesforce scenario suite in `.context/test_self_healing_scenarios.py`; `bruin validate --fast pipelines/credit_union_dwh` | Passed except Bruin credential blocker | Skill validation passed after adding required YAML frontmatter. Repo `score-format` apply inserted the intentional bronze/silver bad casts and `--revert` removed all markers with no residual diff. Repo `metric-description` apply changed the KPI label and `--revert` restored it with no residual diff. Salesforce apply dry-runs connected and planned custom field creation plus one Opportunity update. Salesforce revert dry-runs originally failed when the custom field was absent; fixed `_clear_opportunity_field` to no-op when the field is absent, then both revert dry-runs passed. Mocked tests cover custom field create/delete, Opportunity populate/clear, and absent-field revert no-op. No live Salesforce writes were made. Bruin validation remains blocked only by missing `.credentials/credit-union/snowflake/rsa_key.p8`. |
| 2026-06-23 | Self-healing agent live test after credential restore | `bruin validate --fast pipelines/credit_union_dwh`; `python3 /Users/bear/.codex/skills/.system/skill-creator/scripts/quick_validate.py .agents/self-healing`; mocked scenario tests; live `salesforce new-attribute --apply --limit 1` and `--revert --apply --limit 0 --delete-field`; live `salesforce score-format --apply --limit 1` and `--revert --apply --limit 0 --delete-field`; Salesforce verification query for non-null scenario values | Passed with Salesforce hard-delete limitation | Bruin validation now passes for all 29 assets. Skill validation passes. Live scenario apply paths created or reused the custom fields, granted FieldPermissions for the current System Administrator profile, and updated one Opportunity. Revert paths cleared all non-null Credit Union Demo Opportunity values; verification returned 0 rows with `Credit_Union_Agent_Test_Tier__c` or `Credit_Union_Agent_Test_Score__c` populated. The Salesforce org blocks Tooling API hard deletion of the custom fields with `INSUFFICIENT_ACCESS_ON_CROSS_REFERENCE_ENTITY`, so the script now treats deletion as best-effort, exits cleanly after value cleanup, and documents `--field-suffix` for fresh additive-field repeat demos. |
| 2026-06-23 | Data activation Salesforce admin skill | Added `.agents/data-activation-salesforce-admin/` with a Slack-agent skill, Bruin/Salesforce auth reference, activation guardrails, and reusable Salesforce Python helper | Done | Skill uses the existing Bruin `salesforce` connection injection pattern from `bronze.seed_salesforce_demo_data`, requires dry-run summaries and approval gates for risky mutations, and supports OAuth access-token, connected-app client-credentials, and username/password/security-token auth shapes without exposing secrets. |
| 2026-06-23 | Data activation Salesforce admin skill verification | `python3 -m py_compile .agents/data-activation-salesforce-admin/scripts/salesforce_activation_client.py`; `python3 /Users/bear/.codex/skills/.system/skill-creator/scripts/quick_validate.py .agents/data-activation-salesforce-admin` | Passed | Helper compiles with the available local Python, and the Codex skill validator reports `Skill is valid!`. `python3.11` is not installed locally, so exact Python 3.11 compile could not be run; helper was written without 3.12-only syntax. |
| 2026-06-23 | Data activation Salesforce admin skill mocked test suite | `uv run --with simple-salesforce --with requests python3 .context/test_data_activation_salesforce_admin.py`; `python3 -m py_compile .agents/data-activation-salesforce-admin/scripts/salesforce_activation_client.py .context/test_data_activation_salesforce_admin.py`; `python3 /Users/bear/.codex/skills/.system/skill-creator/scripts/quick_validate.py .agents/data-activation-salesforce-admin` | Passed after hardening | The mocked suite covers required skill files, Bruin secret-injection text, Salesforce base URL and My Domain fallback, OAuth access-token auth, connected-app client-credentials token minting, username/password/security-token fallback, SOQL lookup batching, dry-run counts, live create/update calls, and missing-`Id` safety. Initial test caught an extra bogus My Domain fallback candidate; helper now uses `elif` so `example.my.salesforce.com` yields `example` but not `example.my`. Helper also now skips missing `Id` matches instead of creating records when `match_field` is `Id`. No live Salesforce writes were made. |
| 2026-06-23 | Data activation Salesforce admin live read-only credential probe | `bruin connections test --name salesforce`; temporary Bruin Python probe asset under `pipelines/credit_union_dwh/assets/bronze/`; `bruin run --no-log-file --start-date 2026-06-23 --end-date 2026-06-24 pipelines/credit_union_dwh/assets/bronze/data_activation_salesforce_probe.py`; then removed the temporary probe asset | Passed | Bruin CLI still reports Salesforce `connections test` is unsupported, so the probe asset tested the real `salesforce` connection via Bruin secret injection. Probe validated 30 assets while the temporary asset existed, authenticated to Salesforce, queried `Organization`, queried one `Account`, used `query_existing_by_field`, dry-ran one existing `Id` update, and dry-ran one missing-`Id` update. Sanitized result: `org_probe_rows=1`, `account_probe_rows=1`, `query_existing_rows=1`, `dry_existing_update_count=1`, `dry_missing_id_created_count=0`, `dry_missing_id_skipped_count=1`, `live_writes=0`. Helper fallback logging was reduced from warning to debug so successful fallback auth does not produce noisy logs. No live Salesforce writes were made. |
| 2026-06-24 | Self-healing demo reset decision | Documentation update only | Planned | For the demo reset, delete only the last 10 days of namespaced Credit Union Salesforce demo rows (`2026-06-14` through `2026-06-23` for the June 24 demo). The user will create the 10 daily Bruin Cloud runs from `main`; no local Cloud-trigger action is needed before discussing scenario script execution. |
| 2026-06-24 | Self-healing demo last-10-days reset | `.context/credit-union_delete_last_10_days_salesforce.py --start-date 2026-06-14 --end-date 2026-06-24 --apply`; then scoped `bruin query --connection snowflake-default` deletes for matching bronze and silver rows | Passed | Salesforce source reset deleted 10 Accounts, 10 Contacts, 10 Leads, 10 Opportunities, 10 Tasks, 10 Events, 10 OpportunityLineItems, and 11 OpportunityContactRoles; CampaignMembers were 0. Snowflake cleanup deleted matching bronze rows and silver rows: account health 10, opportunity pipeline 10, product pipeline 10, activity timeline 20. Verification returned 0 remaining Salesforce rows and 0 remaining Snowflake bronze/silver rows for the reset window. The user will create the 10 daily Bruin Cloud runs from `main`; no local Cloud-trigger action was taken. |
| 2026-06-24 | Scenario 1 additive Salesforce field | `uv run --with simple-salesforce --with pyyaml python3 .agents/self-healing/scenarios/self_healing_scenarios.py salesforce new-attribute --apply --limit 25 --field-suffix june15` | Passed | Created `Opportunity.Credit_Union_Agent_Test_Tier_june15__c`, created FieldPermissions for the current profile, and populated 25 Credit Union Demo Opportunity rows. Dry-run was run first and showed the same planned scope. |
| 2026-06-24 | Scenario 1 Cloud trigger | `bruin cloud runs trigger --project-id 01kvqkcm7pg35gcggxwdrkx7hf --pipeline credit_union_dwh --start-date 2026-06-15T00:00:00Z --end-date 2026-06-16T00:00:00Z --note "scenario 1 additive Salesforce field for June 15 demo" --output json`; then `bruin cloud runs list --project-id 01kvqkcm7pg35gcggxwdrkx7hf --pipeline credit_union_dwh --limit 1 --output json` | Running | Trigger succeeded for Bruin's exclusive interval covering June 15. Run ID: `manual__2026-06-24T13:30:43+00:00`; data interval `2026-06-15 00:00:00Z` to `2026-06-16 00:00:00Z`; Cloud status was still `running` at first poll. |
| 2026-06-24 | Scenario 2 score-format source and repo issue | `uv run --with simple-salesforce --with pyyaml python3 .agents/self-healing/scenarios/self_healing_scenarios.py salesforce score-format --apply --limit 25`; `python3 .agents/self-healing/scenarios/self_healing_scenarios.py repo score-format --apply`; PR #13 merged to `main` at `ab3f499` | Passed | Salesforce field `Opportunity.Credit_Union_Agent_Test_Score__c` already existed; FieldPermissions were updated and 25 Credit Union Demo Opportunity rows were populated with string score values. Repo mutation added intentional integer typing/casting markers in `bronze.salesforce_opportunities` and `silver.salesforce_opportunity_pipeline`; PR #13 made the failure visible to Bruin Cloud. Full local `bruin validate --fast` was blocked by an unrelated missing Snowflake key file, but both modified assets passed `bruin internal parse-asset`. |
| 2026-06-24 | Scenario 2 Cloud trigger | `bruin cloud runs trigger --project-id 01kvqkcm7pg35gcggxwdrkx7hf --pipeline credit_union_dwh --start-date 2026-06-16T00:00:00Z --end-date 2026-06-17T00:00:00Z --note "scenario 2 score-format drift for June 16 demo" --output json`; then `bruin cloud instances failed-logs --project-id 01kvqkcm7pg35gcggxwdrkx7hf --pipeline credit_union_dwh --run-id 'manual__2026-06-24T13:59:14+00:00'` | Failed as intended | Trigger succeeded for Bruin's exclusive interval covering June 16. Run ID: `manual__2026-06-24T13:59:14+00:00`; data interval `2026-06-16 00:00:00Z` to `2026-06-17 00:00:00Z`; run started `2026-06-24 13:59:14Z`, ended `2026-06-24 14:05:40Z`, wall time `00:06:26`. `silver.salesforce_opportunity_pipeline` failed with Snowflake query `01c543cb-0000-60f3-0001-003e0006c732`: `SQL compilation error: error line 134 at position 193 - invalid identifier 'AGENT_TEST_SCORE'`. This is ready for Slack agent diagnosis/fix. |
| 2026-06-24 | Scenario 2 failure investigation and repo fix | `bruin cloud runs diagnose --project-id 01kvqkcm7pg35gcggxwdrkx7hf --pipeline credit_union_dwh --run-id manual__2026-06-24T13:59:14+00:00 --output json`; failed logs for `silver.salesforce_opportunity_pipeline`; Cloud asset reads; Snowflake information-schema and source coverage queries; `bruin format pipelines/credit_union_dwh`; `bruin validate --fast pipelines/credit_union_dwh`; read-only projection compile query | Fix prepared | Run failed on `silver.salesforce_opportunity_pipeline` with Snowflake `invalid identifier 'AGENT_TEST_SCORE'` because the existing silver target table did not yet have the new column while the merge SQL tried to update/insert it. Cloud bronze logs also showed the root scenario issue: Salesforce reported `Credit_Union_Agent_Test_Score__c` as string, but the repo forced it to `int32`. The repo fix changes bronze and silver score metadata to `VARCHAR` and uses `TO_VARCHAR` in silver. Validation passed for all 29 assets, and the read-only projection compiled over 202 Opportunity rows. Current bronze has 0 non-null score values because the failed scenario ingestion coerced the string source through the bad numeric contract; after the fix is merged, recovery should use a human-approved narrow Cloud full refresh from `bronze.salesforce_opportunities` downstream for the scenario interval so bronze and silver schemas are rebuilt with text score columns. |
| 2026-06-24 | Scenario 2 Cloud recovery after PR #17 | `gh pr merge 17 --squash --delete-branch`; `bruin cloud runs trigger --project-id 01kvqkcm7pg35gcggxwdrkx7hf --pipeline credit_union_dwh --asset bronze.salesforce_opportunities --downstream --full-refresh --start-date 2026-06-16T00:00:00Z --end-date 2026-06-17T00:00:00Z --note "recover scenario 2 score-format drift after VARCHAR fix" --output json`; Cloud run/status checks; Snowflake verification queries | Passed | PR #17 merged to `main` at `b3f0f9d` at `2026-06-24 14:14:40Z`. Recovery run `manual__2026-06-24T14:14:58+00:00` succeeded for the June 16 interval in `00:03:21`; original failed asset `silver.salesforce_opportunity_pipeline` passed. Destination verification: `bronze.salesforce_opportunities.CREDIT_UNION_AGENT_TEST_SCORE__C` and `silver.salesforce_opportunity_pipeline.AGENT_TEST_SCORE` are `TEXT`; both bronze and silver Opportunity tables have 202 rows and 25 non-null score rows with values spanning `SCORE-100` to `SCORE-109`. Downstream gold row counts: activity coverage 6, daily channel 148, monthly channel 58, stage 5, KPIs 4. |
| 2026-06-24 | Add Opportunity test tier downstream | `bruin format pipelines/credit_union_dwh`; `bruin validate --fast pipelines/credit_union_dwh`; targeted full-refresh runs for `silver.salesforce_opportunity_pipeline`, `silver.salesforce_product_pipeline`, `gold.pipeline_by_channel_daily`, `gold.pipeline_by_channel_monthly`, and `gold.product_pipeline_performance`; downstream Snowflake verification queries | Passed | Added the additive Salesforce Opportunity field `Credit_Union_Agent_Test_Tier_June15__c` to the bronze contract and exposed it downstream as `opportunity_test_tier`. Validation passed for all 29 assets. Targeted runs passed with checks: silver Opportunity Pipeline 9, silver Product Pipeline 7, gold Daily Channel 7, gold Monthly Channel 7, and gold Product Pipeline Performance 5. Verification confirmed `OPPORTUNITY_TEST_TIER` exists in all five downstream tables and carries 25 populated Opportunity rows across Branch Priority, Cross Sell, Digital Follow-up, and Member Growth; null source values are surfaced as `Unspecified`. |
| 2026-06-24 | Merge Opportunity test tier PR and Cloud full refresh | `gh pr merge 18 --squash --delete-branch`; `bruin cloud runs trigger --project-id 01kvqkcm7pg35gcggxwdrkx7hf --pipeline credit_union_dwh --asset silver.salesforce_opportunity_pipeline --asset silver.salesforce_product_pipeline --asset gold.pipeline_by_channel_daily --asset gold.pipeline_by_channel_monthly --asset gold.product_pipeline_performance --full-refresh --start-date 2026-06-15T00:00:00Z --end-date 2026-06-17T00:00:00Z --note "full refresh affected Opportunity test tier downstream tables after PR #18" --output json`; Cloud run/status checks; Snowflake verification queries | Passed | PR #18 merged to `main` at `16b8e2f` at `2026-06-24 14:20:59Z`. Cloud had synced commit `16b8e2f` before the refresh. Run `manual__2026-06-24T14:21:48+00:00` succeeded for the June 15-17 interval in `00:01:21`; selected assets refreshed successfully: silver Opportunity Pipeline 9 checks, silver Product Pipeline 7 checks, gold Product Pipeline Performance 5 checks, gold Daily Channel 7 checks, and gold Monthly Channel 7 checks. Verification confirmed `OPPORTUNITY_TEST_TIER` exists as `TEXT` in all five affected tables. Opportunity-grain rollups show Branch Priority 7, Cross Sell 6, Digital Follow-up 6, Member Growth 6, and Unspecified 177; product-line rollups show the same 25 populated tier rows plus 146 Unspecified line items. |
| 2026-06-24 | Scenario 3 metric-definition label issue | `python3 .agents/self-healing/scenarios/self_healing_scenarios.py repo metric-description --apply`; `bruin internal parse-asset pipelines/credit_union_dwh/assets/gold/pipeline_kpis.sql`; `bruin validate --fast pipelines/credit_union_dwh` | Prepared | Changed only the `gold.pipeline_kpis` display label for `activity_coverage_pct` from `Opportunities with activity` to `Average approved loan APR`. The metric key and SQL calculation are unchanged. Asset parse passed. Full fast validation was blocked before asset validation by an unrelated missing Snowflake key file. No pipeline or Cloud run was triggered. |
| 2026-06-24 | Scenario 3 metric label recovery | PR #21; `bruin format pipelines/credit_union_dwh`; `bruin internal parse-asset pipelines/credit_union_dwh/assets/gold/pipeline_kpis.sql`; `bruin validate --fast pipelines/credit_union_dwh`; `bruin cloud runs trigger --project-id 01kvqkcm7pg35gcggxwdrkx7hf --pipeline credit_union_dwh --asset gold.pipeline_kpis --start-date 2026-06-23T00:00:00Z --end-date 2026-06-24T00:00:00Z --note "restore activity coverage KPI label after PR #21" --output json`; Snowflake verification queries | Passed | Restored `gold.pipeline_kpis.activity_coverage_pct` label from `Average approved loan APR` to `Opportunities with activity` without changing the activity-coverage calculation. PR #21 merged to `main` at `a73bdf5`. Cloud asset sync was verified before triggering. Scoped Cloud run `manual__2026-06-24T19:02:03+00:00` succeeded in `00:00:18` for the June 23-24 interval. Snowflake verification returned `activity_coverage_pct`, `Opportunities with activity`, `0.846535`. 2026 opportunity summary using `activity_count > 0`: 202 total opportunities, 171 with activity, 171 total activities, 89 completed activities, and $17.319M active opportunity amount. |
| 2026-06-26 | Generic credit union rename | Renamed the client folder to `credit-union/`, renamed the pipeline to `credit_union_dwh`, replaced named-client prefixes in tracked assets/docs/agent context, ran `bruin format pipelines/credit_union_dwh`, Python compile checks, and `bruin validate --fast --config-file .context/bruin-validate-credit-union.yml pipelines/credit_union_dwh` | Passed | Fast validation passed for all 29 assets with a temporary dummy config that avoids unrelated broken local credentials. Direct validation against `.bruin.yml` is currently blocked before asset validation by a missing unrelated Red Bull Snowflake key file. Tracked repo scan has no remaining named-client references. Ignored local `.context`, `logs`, and `.credentials` paths were not rewritten. |
| 2026-06-26 | Snowflake database rename setup | Copied the ignored local Snowflake key to `.credentials/credit-union/snowflake/rsa_key.p8`, updated root `.bruin.yml` `snowflake-default` from the previous demo database to `CREDIT_UNION_DEMO`, created `CREDIT_UNION_DEMO`, and ensured `BRONZE`, `SILVER`, `GOLD`, and `_BRUIN_STAGING` schemas exist using `bruin query` with a temporary single-connection config | Passed | No Bruin assets were run. Verification query returned `CURRENT_DATABASE() = CREDIT_UNION_DEMO` and `CURRENT_SCHEMA() = BRONZE`. The temporary `.context/bruin-snowflake-default.yml` contains only the copied `snowflake-default` connection for CLI checks because root `.bruin.yml` still has an unrelated broken Red Bull credential path. |

## Open Decisions

- Desired demo data volume for standard backfills now that historical full refresh generates every date. For the self-healing demo, use the existing default 1/1/1/1/1/1 daily volume.
- Whether to enable Campaign creation for the Salesforce user or pre-seed
  CampaignMember rows, so the marketing funnel can show non-empty attribution
  metrics.
- Bruin Cloud Snowflake fix path: deploy the local `gold.pipeline_by_channel_monthly`
  `create+replace` materialization change, then rerun that asset in Cloud.
- New `gold.pipeline_by_channel_daily` time-interval asset needs the same
  deploy path and an initial Cloud `--full-refresh` bootstrap before normal
  interval runs if the Cloud target table is absent.
- Durable Salesforce Cloud auth path: username/password/security-token works
  only when Salesforce SOAP API login is enabled. Direct connected-app
  `client_id`/`client_secret` worked against Salesforce OAuth but did not work
  with Bruin ingestr locally.
- Whether Salesforce demo data should be generated only in a sandbox org or namespaced with a credit union demo prefix in a shared org.
- For larger demos, use a Salesforce org with more storage or switch seed writes to a smaller volume. The current default is 1 account/day, 1 contact/account, 1 opportunity/account, and 1 task/opportunity.
