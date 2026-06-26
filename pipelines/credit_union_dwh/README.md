# Credit Union DWH Pipeline

This pipeline seeds realistic demo records into Salesforce, ingests Salesforce
standard objects into Snowflake with Bruin ingestr assets, and builds silver and
gold tables for a credit union CRM analytics demo.

## Data Sources

- **Salesforce Sales Cloud** via the repo-local Bruin `salesforce` connection.
  Standard objects used: `Account`, `Contact`, `Lead`, `Campaign`, `User`,
  `Product2`, `Pricebook2`, `PricebookEntry`, `Opportunity`,
  `OpportunityContactRole`, `OpportunityLineItem`, `Task`, and `Event`.
- **Synthetic credit union demo generator** in
  `assets/bronze/seed_salesforce_demo_data.py`. It creates deterministic
  member-group accounts, contacts, member-acquisition leads, product catalog
  rows, lending/card/deposit opportunities, opportunity line items, contact
  roles, banker tasks, and appointment events in Salesforce for the Bruin
  interval. The seed asset has no Python materialization; it writes to
  Salesforce only and logs object-level counts. In this org Campaign is
  queryable but not createable for the current user, so Campaign/CampaignMember
  seed writes are skipped without failing. If the Salesforce dev org reaches
  storage limits, the seed updates existing demo records and skips new creates
  so the warehouse ingestion can continue; set
  `CREDIT_UNION_FAIL_ON_STORAGE_LIMIT=1` to make storage exhaustion fail the
  seed step.

## Datasets

- Bronze: `bronze`
- Silver: `silver`
- Gold: `gold`

## Assets

### Bronze

| Asset | Type | Description |
|---|---|---|
| `bronze.seed_salesforce_demo_data` | Python | Upserts deterministic interval-based demo records into Salesforce. |
| `bronze.salesforce_accounts` | ingestr | Syncs Salesforce `account` into Snowflake with merge on `systemmodstamp`. |
| `bronze.salesforce_contacts` | ingestr | Syncs Salesforce `contact` into Snowflake with merge on `systemmodstamp`. |
| `bronze.salesforce_leads` | ingestr | Syncs Salesforce `lead` for member acquisition funnel demos. |
| `bronze.salesforce_campaigns` | ingestr | Syncs Salesforce `campaign` for community outreach and marketing attribution. |
| `bronze.salesforce_campaign_members` | SQL | Creates a source-shaped empty CampaignMember table because this org has no campaign members and ingestr currently fails on empty CampaignMember extracts. |
| `bronze.salesforce_users` | ingestr | Syncs Salesforce `user` for banker and owner attribution after the seed step succeeds. |
| `bronze.salesforce_products` | ingestr | Syncs Salesforce `product` / Product2 for product catalog analytics. |
| `bronze.salesforce_pricebooks` | ingestr | Syncs Salesforce `pricebook` / Pricebook2. |
| `bronze.salesforce_pricebook_entries` | ingestr | Syncs Salesforce `pricebook_entry` for product pricing. |
| `bronze.salesforce_opportunities` | ingestr | Syncs Salesforce `opportunity` into Snowflake with merge on `systemmodstamp`. |
| `bronze.salesforce_opportunity_contact_roles` | ingestr | Syncs Salesforce `opportunity_contact_role` for member decision-maker roles. |
| `bronze.salesforce_opportunity_line_items` | ingestr | Syncs Salesforce `opportunity_line_item` for product-grain pipeline analytics. |
| `bronze.salesforce_tasks` | ingestr | Syncs Salesforce `task` into Snowflake with merge on `systemmodstamp`. |
| `bronze.salesforce_events` | ingestr | Syncs Salesforce `event` for appointments and banker meetings. |

### Silver

| Asset | Description |
|---|---|
| `silver.salesforce_account_health` | Account-grain mart joining accounts, contacts, opportunities, and tasks with pipeline and engagement metrics. |
| `silver.salesforce_opportunity_pipeline` | Opportunity-grain mart with product family, stage group, weighted amount, close month, and activity coverage. |
| `silver.salesforce_product_pipeline` | Product-line-item mart joining opportunities, products, pricebooks, and users. |
| `silver.salesforce_marketing_funnel` | Campaign-member mart for campaigns, leads, contacts, and accounts. Empty until CampaignMember rows exist in the org. |
| `silver.salesforce_activity_timeline` | Unified Task and Event timeline for banker follow-up and appointments. |

### Gold

| Asset | Description |
|---|---|
| `gold.pipeline_kpis` | Executive KPI rollup for accounts, open pipeline, weighted pipeline, and activity coverage. |
| `gold.pipeline_by_stage` | Stage-group pipeline value, weighted value, probability, and completed activity. |
| `gold.pipeline_by_channel_daily` | Daily open and won pipeline by lead source; uses Bruin `time_interval` materialization on `close_date`. |
| `gold.pipeline_by_channel_monthly` | Monthly open and won pipeline by lead source. |
| `gold.activity_coverage_by_product` | Product-family pipeline and banker activity coverage. |
| `gold.product_pipeline_performance` | Product/month pipeline performance from OpportunityLineItem. |
| `gold.campaign_conversion_funnel` | Campaign conversion funnel. Empty until CampaignMember rows exist in the org. |
| `gold.branch_relationship_health` | Branch-market relationship health scorecard. |
| `gold.banker_activity_coverage` | Banker activity and owned product pipeline coverage. |

## Dependency Notes

- `bronze.seed_salesforce_demo_data` is upstream of all Salesforce bronze
  extracts, including `bronze.salesforce_users`, so a seed failure blocks the
  source sync layer and keeps the demo run graph honest.
- `bronze.salesforce_campaign_members` depends on
  `bronze.salesforce_campaigns` even though it is currently a source-shaped
  empty SQL shim. This keeps marketing lineage tied to Campaign until
  CampaignMember rows are available in the org.
- `silver.salesforce_activity_timeline` depends only on Tasks, Events,
  Opportunities, and Users. It gets `account_id` from Opportunity and does not
  read the Account bronze table directly.

## Run Commands

### Salesforce connection

The pipeline expects a Bruin Salesforce connection named `salesforce`. With
the current Bruin Salesforce ingestr connector, the supported runtime options
are an OAuth access token or username/password/security-token auth. Direct
Salesforce connected-app `client_id`/`client_secret` fields were tested locally
and are not accepted by ingestr yet.

Interactive local demo using Salesforce CLI:

```bash
uv tool install --force ingestr@latest
sf org login web --instance-url https://orgfarm-a232e145a7-dev-ed.develop.my.salesforce.com
sf org auth show-access-token --target-org <salesforce-username>
```

Then configure `.bruin.yml` locally with:

```yaml
salesforce:
  - name: salesforce
    access_token: "<oauth-access-token>"
    domain: "https://orgfarm-a232e145a7-dev-ed.develop.my.salesforce.com"
```

For Bruin Cloud scheduled runs, username/password/security-token auth can be
used after Salesforce SOAP API login is enabled in the org:

```yaml
salesforce:
  - name: salesforce
    username: "<salesforce-username>"
    password: "<salesforce-password>"
    token: "<salesforce-security-token>"
    domain: "https://orgfarm-a232e145a7-dev-ed.develop.my.salesforce.com"
```

Salesforce setup required for this auth path:

1. In Salesforce Setup, open `User Interface`.
2. Under `API Settings`, enable `Enable SOAP API Login`.
3. Reset the security token for the Salesforce user and use that exact token in
   Bruin Cloud.
4. Confirm the Bruin Cloud connection name is exactly `salesforce`.

If SOAP login cannot be enabled, use the OAuth access-token field in Bruin Cloud
instead. Access tokens work with Bruin but expire, so they are less durable for
scheduled runs.

Validate all asset definitions:

```bash
bruin validate --fast pipelines/credit_union_dwh
```

Run the full demo pipeline with one generated record set per historical day:

```bash
CREDIT_UNION_ACCOUNTS_PER_DAY=1 \
CREDIT_UNION_CONTACTS_PER_ACCOUNT=1 \
CREDIT_UNION_OPPORTUNITIES_PER_ACCOUNT=1 \
CREDIT_UNION_TASKS_PER_OPPORTUNITY=1 \
CREDIT_UNION_LEADS_PER_DAY=1 \
CREDIT_UNION_EVENTS_PER_OPPORTUNITY=1 \
bruin run --full-refresh --start-date 2015-01-01 --end-date 2026-06-23 \
  pipelines/credit_union_dwh
```

For long full-refresh intervals, the seed asset now generates every date in the
requested Bruin interval. This can create thousands of Salesforce records from a
2015 start date, so use lower `CREDIT_UNION_*` volumes or a Salesforce org with enough
storage when running historical full refreshes. By default, Salesforce storage
limit errors skip new demo creates and continue the pipeline; use
`CREDIT_UNION_FAIL_ON_STORAGE_LIMIT=1` when you need strict source seeding.

Dry-run the Salesforce demo generator without writing to Salesforce:

```bash
CREDIT_UNION_DRY_RUN=1 \
CREDIT_UNION_ACCOUNTS_PER_DAY=1 \
bruin run --start-date 2015-01-01 --end-date 2015-01-02 \
  pipelines/credit_union_dwh/assets/bronze/seed_salesforce_demo_data.py
```

Seed historical Salesforce demo data. The generator is deterministic by Bruin
interval, so reruns update the same Account, Contact, Opportunity, and Task
records instead of creating duplicates.

```bash
CREDIT_UNION_ACCOUNTS_PER_DAY=1 \
CREDIT_UNION_CONTACTS_PER_ACCOUNT=1 \
CREDIT_UNION_OPPORTUNITIES_PER_ACCOUNT=1 \
CREDIT_UNION_TASKS_PER_OPPORTUNITY=1 \
CREDIT_UNION_LEADS_PER_DAY=1 \
CREDIT_UNION_EVENTS_PER_OPPORTUNITY=1 \
bruin run --start-date 2026-06-22 --end-date 2026-06-23 \
  pipelines/credit_union_dwh/assets/bronze/seed_salesforce_demo_data.py
```

For the first Snowflake ingestion after seeding, prefer a full refresh. The seed
asset creates historical business dates such as Opportunity `CloseDate` and
Task `ActivityDate`, but Salesforce `SystemModstamp` reflects the actual write
time in Salesforce.

```bash
bruin run --full-refresh pipelines/credit_union_dwh/assets/bronze/salesforce_accounts.asset.yml
bruin run --full-refresh pipelines/credit_union_dwh/assets/bronze/salesforce_contacts.asset.yml
bruin run --full-refresh pipelines/credit_union_dwh/assets/bronze/salesforce_leads.asset.yml
bruin run --full-refresh pipelines/credit_union_dwh/assets/bronze/salesforce_campaigns.asset.yml
bruin run --full-refresh pipelines/credit_union_dwh/assets/bronze/salesforce_campaign_members.sql
bruin run --full-refresh pipelines/credit_union_dwh/assets/bronze/salesforce_users.asset.yml
bruin run --full-refresh pipelines/credit_union_dwh/assets/bronze/salesforce_products.asset.yml
bruin run --full-refresh pipelines/credit_union_dwh/assets/bronze/salesforce_pricebooks.asset.yml
bruin run --full-refresh pipelines/credit_union_dwh/assets/bronze/salesforce_pricebook_entries.asset.yml
bruin run --full-refresh pipelines/credit_union_dwh/assets/bronze/salesforce_opportunities.asset.yml
bruin run --full-refresh pipelines/credit_union_dwh/assets/bronze/salesforce_opportunity_contact_roles.asset.yml
bruin run --full-refresh pipelines/credit_union_dwh/assets/bronze/salesforce_opportunity_line_items.asset.yml
bruin run --full-refresh pipelines/credit_union_dwh/assets/bronze/salesforce_tasks.asset.yml
bruin run --full-refresh pipelines/credit_union_dwh/assets/bronze/salesforce_events.asset.yml
```

Build silver and gold tables:

```bash
bruin run pipelines/credit_union_dwh/assets/silver/salesforce_opportunity_pipeline.sql
bruin run pipelines/credit_union_dwh/assets/silver/salesforce_account_health.sql
bruin run pipelines/credit_union_dwh/assets/silver/salesforce_product_pipeline.sql
bruin run pipelines/credit_union_dwh/assets/silver/salesforce_marketing_funnel.sql
bruin run pipelines/credit_union_dwh/assets/silver/salesforce_activity_timeline.sql
bruin run pipelines/credit_union_dwh/assets/gold/pipeline_kpis.sql
bruin run pipelines/credit_union_dwh/assets/gold/pipeline_by_stage.sql
bruin run pipelines/credit_union_dwh/assets/gold/pipeline_by_channel_daily.sql
bruin run pipelines/credit_union_dwh/assets/gold/pipeline_by_channel_monthly.sql
bruin run pipelines/credit_union_dwh/assets/gold/activity_coverage_by_product.sql
bruin run pipelines/credit_union_dwh/assets/gold/product_pipeline_performance.sql
bruin run pipelines/credit_union_dwh/assets/gold/campaign_conversion_funnel.sql
bruin run pipelines/credit_union_dwh/assets/gold/branch_relationship_health.sql
bruin run pipelines/credit_union_dwh/assets/gold/banker_activity_coverage.sql
```

Or run downstream once the bronze objects are populated:

```bash
bruin run --downstream pipelines/credit_union_dwh/assets/bronze/salesforce_accounts.asset.yml
bruin run --downstream pipelines/credit_union_dwh/assets/bronze/salesforce_opportunities.asset.yml
```

Run the full expanded daily demo end to end:

```bash
CREDIT_UNION_ACCOUNTS_PER_DAY=1 \
CREDIT_UNION_CONTACTS_PER_ACCOUNT=1 \
CREDIT_UNION_OPPORTUNITIES_PER_ACCOUNT=1 \
CREDIT_UNION_TASKS_PER_OPPORTUNITY=1 \
CREDIT_UNION_LEADS_PER_DAY=1 \
CREDIT_UNION_EVENTS_PER_OPPORTUNITY=1 \
bruin run --start-date 2026-06-23 --end-date 2026-06-24 \
  pipelines/credit_union_dwh
```

## Known Limitations

- Salesforce credentials live in the gitignored repo-root `.bruin.yml`. No
  credentials are committed in this pipeline.
- The storage-safe six-month demo volume is 1 account per day, 1 contact per
  account, 1 opportunity per account, 1 task per opportunity, 1 lead per day,
  and 1 event per opportunity. Products and PricebookEntries are fixed catalog
  rows that are updated on each seed run.
- The pipeline start date is now `2015-01-01`. Long full-refresh seed runs now
  generate one record set per historical day in the interval, so storage use can
  be high in small Salesforce dev orgs. When storage is exhausted, the seed
  logs skipped creates and lets the Salesforce-to-Snowflake ingestion continue
  over whatever source records already exist.
- Historical dummy business activity is stored in Salesforce business fields,
  not Salesforce audit fields. Use full refresh for the first bronze ingestion
  after seeding; then use normal incremental runs on `SystemModstamp`.
- Current materialization strategy:
  - Bronze Salesforce ingestr assets use `incremental_strategy: merge`,
    `incremental_key: SystemModstamp`, schema enforcement, and Snowflake
    clustering on incremental/date fields.
  - Core account/opportunity silver marts use Bruin `merge` materialization and
    only recompute accounts/opportunities touched by source `SystemModstamp` in
    the Bruin interval during normal runs. Product, marketing, and activity
    silver marts use `create+replace` because they are small demo-friendly
    tables over current CRM state.
  - `gold.pipeline_by_channel_daily` uses Bruin `time_interval`
    materialization with `close_date` as the date-grain `incremental_key`.
    Bootstrap it once with `--full-refresh` before normal interval runs if the
    target table does not already exist.
  - `gold.pipeline_by_channel_monthly` uses `create+replace` table
    materialization over the current silver mart. It previously used
    `delete+insert`, but Bruin Cloud failed when Snowflake had no current schema
    for the unqualified temp table used by that strategy.
- To refresh the local OAuth token for Bruin, run `sf org login web`, then pipe
  `sf org auth show-access-token --target-org credit-union-salesforce --json` into a
  local `.bruin.yml` updater. Do not use `sf org display`; current Salesforce
  CLI versions return a redacted placeholder there.
- On 2026-06-19, the default historical seed volume hit this Salesforce dev
  org's storage limit after creating/updating Accounts and Contacts and part of
  Opportunities. The partial data was cleared and reseeded with smaller
  `CREDIT_UNION_*` volumes. The Snowflake pipeline reuses that Salesforce source.
- The local `snowflake-default` connection was initially configured with
  database `USER$ARSALAN`, which Snowflake rejected for table creation because it
  is a personal database. The local connection now points to `CREDIT_UNION_DEMO`, with
  `BRONZE`, `SILVER`, `GOLD`, and `_BRUIN_STAGING` schemas created.
- The local `snowflake-default` connection should not set a `region` value for
  this account. A regional hostname caused TLS certificate verification failures
  in Bruin's native Snowflake SQL runner.
- All bronze Salesforce extract assets depend on
  `bronze.seed_salesforce_demo_data`, so lineage records the Salesforce seeding
  step as the upstream source generator and unexpected seed failures stop the
  extract layer. Salesforce storage-limit create skips are treated as a
  controlled demo-org condition unless `CREDIT_UNION_FAIL_ON_STORAGE_LIMIT=1`.
- On 2026-06-22, a requested 2015 full refresh could not start because the local
  Snowflake private key file referenced by `.bruin.yml` was missing at
  `.credentials/credit-union/snowflake/rsa_key.p8`. No Salesforce or Snowflake data
  was changed by that attempt.
- Bruin ingestr requires `--start-date` to be earlier than `--end-date`.
  Treat scheduled/daily run windows as `[start-date, end-date)`. For example,
  use `--start-date 2026-06-22 --end-date 2026-06-23` to generate and ingest
  the June 22 daily interval.
- Bruin Cloud Salesforce username/password/security-token auth failed until
  Salesforce SOAP API login was enabled. After enabling SOAP API login, the
  2026-06-23 Cloud retry passed seed, all bronze ingestr assets, both silver
  assets, and three of four gold assets.
- The 2026-06-23 Bruin Cloud run failed on `gold.pipeline_by_channel_monthly`
  because the previous `delete+insert` strategy created an unqualified temp
  table in a Snowflake session with no current schema. The asset now uses
  `create+replace` to avoid that temp-table path.
- This Salesforce org allows querying Campaign but does not allow inserting new
  Campaign records for the current user. The seed asset detects that and skips
  Campaign/CampaignMember creation without failing. Existing Campaign rows are
  still ingested; `bronze.salesforce_campaign_members` is a source-shaped empty
  Snowflake table until CampaignMember rows are available.

## Latest 2026-06-26 Verification

On 2026-06-26, the restored expanded Salesforce pipeline was verified locally
against the configured Salesforce and Snowflake connections.

- Historical warehouse backfill: `CREDIT_UNION_DRY_RUN=1 bruin run --workers 1
  --full-refresh --start-date 2015-01-01 --end-date 2026-06-26
  pipelines/credit_union_dwh` passed with 29 assets and 140 quality checks in
  4m23s. The seed used dry-run mode for the historical interval because the
  Salesforce dev org had reached storage limits; the bronze ingestr assets still
  read Salesforce and loaded Snowflake.
- Daily incremental run: `bruin run --workers 1 --start-date 2026-06-26
  --end-date 2026-06-27 pipelines/credit_union_dwh` passed with 29 assets and
  140 quality checks in 3m33s. The seed updated existing records where possible
  and skipped new creates blocked by Salesforce storage limits.
- Verified Snowflake row counts after the daily run: bronze Accounts 1,793,
  Contacts 195, Leads 197, Campaigns 4, CampaignMembers 0, Users 8, Products
  26, Pricebooks 2, PricebookEntries 43, Opportunities 206,
  OpportunityContactRoles 178, OpportunityLineItems 175, Tasks 183, Events 175;
  silver AccountHealth 1,793, OpportunityPipeline 206, ProductPipeline 175,
  MarketingFunnel 0, ActivityTimeline 358; gold KPI/stage/channel/product/
  branch/banker rollups all built successfully.

## Latest Expanded Salesforce Pipeline Run

On 2026-06-23, the expanded Salesforce pipeline ran end to end for the daily
interval `2026-06-23` to `2026-06-24`.

- Command: `CREDIT_UNION_ACCOUNTS_PER_DAY=1 CREDIT_UNION_CONTACTS_PER_ACCOUNT=1 CREDIT_UNION_OPPORTUNITIES_PER_ACCOUNT=1 CREDIT_UNION_TASKS_PER_OPPORTUNITY=1 CREDIT_UNION_LEADS_PER_DAY=1 CREDIT_UNION_EVENTS_PER_OPPORTUNITY=1 bruin run --start-date 2026-06-23 --end-date 2026-06-24 pipelines/credit_union_dwh`
- Result: 29 assets succeeded and 138 quality checks succeeded in 33.31s.
- Seed created one Account, Contact, Lead, Opportunity, OpportunityContactRole,
  OpportunityLineItem, Task, and Event for the day; updated 9 Products and 9
  PricebookEntries; skipped one Campaign because Campaign is not createable in
  this org.
- Verified Snowflake row counts after the run: bronze Accounts 590, Contacts
  478, Leads 24, Campaigns 4, CampaignMembers 0, Users 8, Products 26,
  Pricebooks 2, PricebookEntries 43, Opportunities 502, OpportunityContactRoles
  2, OpportunityLineItems 2, Tasks 471, Events 2; silver AccountHealth 590,
  OpportunityPipeline 502, ProductPipeline 2, MarketingFunnel 0,
  ActivityTimeline 473; gold KPI/stage/channel/product/branch/banker rollups all
  built successfully.

## Current 2015 Incremental Upgrade Status

On 2026-06-22, the pipeline was updated for `2015-01-01` start-date semantics and
new-data-only daily processing:

- `pipeline.yml` now starts at `2015-01-01`.
- `bronze.seed_salesforce_demo_data` now allows 2015 intervals, defaults to
  1/1/1/1 object volume, and generates every date in the requested Bruin
  interval.
- `bruin ai enhance` was run. The default Claude provider failed because the
  selected model was unavailable; retrying with `claude-sonnet-4-5-20250929`
  reached validation but stopped on the missing Snowflake key. Manual metadata,
  tags, domains, and quality checks were added where safe.
- `bruin format pipelines/credit_union_dwh` passed.
- `python3 -m py_compile .../seed_salesforce_demo_data.py` passed.
- `bruin internal parse-asset` passed for all 11 assets.
- `bruin validate --fast pipelines/credit_union_dwh` and the requested
  full-refresh command were blocked before execution by the missing Snowflake
  key file.
- After restoring credentials, `bruin validate --fast` passed and the 2015 full
  refresh succeeded using an exclusive end date of `2026-06-23`.

## Previous 2015 Full-Refresh Run

On 2026-06-22, the Snowflake pipeline ran end to end for `2015-01-01` through
`2026-06-22` using:

```bash
CREDIT_UNION_ACCOUNTS_PER_DAY=1 \
CREDIT_UNION_CONTACTS_PER_ACCOUNT=1 \
CREDIT_UNION_OPPORTUNITIES_PER_ACCOUNT=1 \
CREDIT_UNION_TASKS_PER_OPPORTUNITY=1 \
bruin run --full-refresh --start-date 2015-01-01 --end-date 2026-06-23 \
  pipelines/credit_union_dwh
```

- Seed asset generated 301 historical business dates under the previous sparse
  historical behavior and updated 301 existing
  Accounts, Contacts, Opportunities, and Tasks with 0 creates and 0 errors.
- Full-refresh run passed for all 11 assets and all 72 quality checks in
  7m40s.
- A normal daily run for `2026-06-22` to `2026-06-23` also passed all 11 assets
  and 72 quality checks in 18s, with the seed updating exactly one Account,
  Contact, Opportunity, and Task.
- Bronze Snowflake: 470 Account rows, 477 Contact rows, 499 Opportunity rows,
  and 468 Task rows. These include existing Salesforce sample records.
- Demo key coverage: generated Account and Contact rows span
  `CREDIT-UNION-DEMO-20150101-001` through `CREDIT-UNION-DEMO-20260622-001`; generated
  Opportunities and Tasks also span those same business-date keys.
- Silver Snowflake: `salesforce_account_health` has 470 rows and
  `salesforce_opportunity_pipeline` has 499 rows.
- Gold Snowflake: `pipeline_kpis` has 4 rows, `pipeline_by_stage` has 5 rows,
  `pipeline_by_channel_monthly` has 167 rows, and
  `activity_coverage_by_product` has 6 rows.

## Latest Bruin Cloud Run

On 2026-06-23, after Salesforce SOAP API login was enabled, Bruin Cloud run
`manual__2026-06-23T13:28:24+00:00` was triggered for the daily interval
`2026-06-22T00:00:00Z` to `2026-06-23T00:00:00Z`.

- `bronze.seed_salesforce_demo_data`: passed.
- All four bronze Salesforce ingestr assets: passed.
- Both silver assets: passed.
- `gold.activity_coverage_by_product`, `gold.pipeline_by_stage`, and
  `gold.pipeline_kpis`: passed.
- `gold.pipeline_by_channel_monthly`: failed.

Failure:

```text
Cannot perform CREATE TEMPTABLE.
This session does not have a current schema.
Call 'USE SCHEMA', or use a qualified name.
```

The Salesforce Cloud connection is no longer the blocker. This asset has since
been changed from `delete+insert` to `create+replace`, and the single-asset local
run passed with all 6 checks.

## Previous Verified Run

On 2026-06-22, the Snowflake pipeline ran end to end for `2026-01-01` through
`2026-06-18`:

- Salesforce source: 169 demo Accounts, Contacts, Opportunities, and Tasks.
- Seed asset updated existing demo records only: 169 Accounts, 169 Contacts, 169
  Opportunities, and 169 Tasks; 0 creates and 0 errors.
- `bruin validate --fast pipelines/credit_union_dwh` passed for
  all 11 assets.
- Bronze Snowflake: 182 Account rows, 189 Contact rows, 200 Opportunity rows,
  and 169 Task rows. The non-demo rows come from existing Salesforce sample data.
- Silver Snowflake: `salesforce_account_health` has 182 rows and
  `salesforce_opportunity_pipeline` has 200 rows.
- Gold Snowflake: `pipeline_kpis` has 4 rows, `pipeline_by_stage` has 5 rows,
  `pipeline_by_channel_monthly` has 49 rows, and
  `activity_coverage_by_product` has 6 rows.
- Opportunity metrics: 200 rows, close dates from `2026-01-12` to
  `2026-08-02`, total amount USD `29,232,913.32`, weighted amount USD
  `19,293,830.30`, and 169 linked activities.
