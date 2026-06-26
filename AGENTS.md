# Data Engineering Agent Instructions

You are a data engineering agent for this repository. Build, maintain, and
review the credit union data warehouse pipeline end to end using Bruin.

## Project Context

- Always read `README.md` before creating or changing assets. Treat it as the
  primary source of project context, including source systems, datasets, run
  commands, limitations, and expected asset layout.
- The documented pipeline is `pipelines/credit_union_dwh`.
- The pipeline ingests Salesforce Sales Cloud data into Snowflake and builds
  bronze, silver, and gold datasets for credit union CRM analytics.
- The documented bronze sources include Salesforce `Account`, `Contact`,
  `Lead`, `Campaign`, `User`, `Product2`, `Pricebook2`, `PricebookEntry`,
  `Opportunity`, `OpportunityContactRole`, `OpportunityLineItem`, `Task`, and
  `Event`.

## Required Tooling

- Use the Bruin MCP for Bruin-specific project inspection, asset guidance,
  lineage, metadata, and validation support whenever available.
- Use the Bruin CLI for all pipeline creation, validation, execution, and
  maintenance workflows.
- You may use the Salesforce CLI to communicate with Salesforce directly for
  discovery and scoping, such as inspecting objects, fields, permissions,
  sample records, and org behavior.
- Do not use the Salesforce CLI to ingest data into the warehouse. Warehouse
  ingestion must be implemented and operated through Bruin assets.
- Prefer Bruin-native commands and asset definitions over ad hoc scripts.
- Validate changed assets with the narrowest useful Bruin CLI command, and
  validate the full pipeline when changes affect shared configuration,
  dependencies, materialization, or multiple layers.

Common commands:

```bash
bruin validate --fast pipelines/credit_union_dwh
bruin run pipelines/credit_union_dwh
bruin run --downstream <asset-path>
bruin run --full-refresh <asset-path>
```

## Layering Rules

- Bronze is for ingestion and source-shaped data. Implement ingestion with
  Bruin `ingestr` YAML assets unless the README documents a specific exception.
- Silver is for cleaned, conformed, business-ready SQL transformation assets.
- Gold is for analytics-ready SQL marts, KPIs, and reporting aggregates.
- Keep dependencies explicit across layers. Bronze assets should feed silver;
  silver assets should feed gold.
- Preserve the credit union CRM domain model described in the README.

## Asset Requirements

Every Bruin asset must include complete operational and catalog metadata:

- Table-level description that explains the grain, source, and business use.
- Column-level descriptions for every output column.
- Quality checks appropriate to the asset grain, such as not-null, uniqueness,
  accepted values, row count, relationship, freshness, or custom SQL checks.
- `owner`.
- Explicit dependencies.
- Useful tags, including layer, source/domain, and business subject tags.
- `meta` fields with relevant operational context, such as source system,
  refresh cadence, grain, primary key, incremental key, business owner, data
  classification, and downstream consumers.

Do not add placeholder descriptions or generic checks. Metadata should be
specific enough for another data engineer or analyst to understand and operate
the asset without reading the SQL first.

## Materialization And Performance

- Choose materialization based on asset grain, data volume, source update
  behavior, and scheduled-load requirements.
- Use incremental or time-interval strategies for regularly updated data when
  they reduce cost and runtime without compromising correctness.
- Use full refresh only when the source or transformation semantics require it,
  such as small reference tables, rebuild-safe demo loads, or assets without a
  reliable incremental key.
- For Salesforce ingestr bronze assets, use the appropriate merge or incremental
  key from Salesforce system fields when available, such as `SystemModstamp`.
- For silver and gold SQL assets, align the incremental key with the business
  event or update date documented by the model, such as close date, activity
  date, campaign member date, or source update timestamp.
- Set partitioning when it materially helps scheduled loads, pruning, or
  retention management.
- Set clustering when common joins, filters, or aggregations will benefit, such
  as account, opportunity, owner, product family, branch, stage, or date fields.
- Document the reasoning for materialization, partitioning, and clustering in
  asset metadata when the choice is not obvious.

## Workflow

1. Read `README.md` and inspect existing Bruin assets before editing.
2. Use Bruin MCP and Bruin CLI to understand asset shape, lineage, and valid
   configuration.
3. Create or update bronze ingestion assets first, then silver transformations,
   then gold marts.
4. Keep SQL transformations deterministic and explicit about grain.
5. Add or update descriptions, checks, dependencies, tags, owners, and `meta`
   fields in the same change as the asset logic.
6. Run Bruin validation before handing work back.
7. When credentials or live connections are unavailable, run metadata/static
   validation and clearly state what could not be executed.
