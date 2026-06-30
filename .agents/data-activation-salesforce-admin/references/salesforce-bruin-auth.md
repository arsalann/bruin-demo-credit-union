# Salesforce Bruin Auth

Use the repo-local Bruin Salesforce connection named `salesforce`. Do not read or print `.bruin.yml`; let Bruin inject the connection into Python assets.

## Bruin asset header

```python
"""@bruin
name: ops.activate_salesforce_example
description: Applies an approved Salesforce activation request.
image: python:3.11

secrets:
  - key: salesforce
    inject_as: SALESFORCE_CONNECTION
@bruin"""
```

Bruin injects non-generic connection details as a JSON string in `SALESFORCE_CONNECTION`.

## Supported connection shapes

Use the same pattern as `pipelines/credit_union_dwh/assets/bronze/seed_salesforce_demo_data.py`.

OAuth access token:

```json
{
  "access_token": "<oauth-access-token>",
  "domain": "https://example.my.salesforce.com"
}
```

Connected-app client credentials:

```json
{
  "grant_type": "client_credentials",
  "client_id": "<connected-app-client-id>",
  "client_secret": "<connected-app-client-secret>",
  "domain": "https://example.my.salesforce.com"
}
```

Username, password, and security token:

```json
{
  "username": "<salesforce-username>",
  "password": "<salesforce-password>",
  "token": "<salesforce-security-token>",
  "domain": "https://example.my.salesforce.com"
}
```

For username/password/token auth in Salesforce orgs, SOAP API login must be enabled. If login fails in Bruin Cloud but local OAuth works, inspect Cloud connection settings and Salesforce login policy before changing activation code.

## Minimal SOQL probe

```python
from salesforce_activation_client import salesforce_from_env

sf = salesforce_from_env()
result = sf.query("SELECT Id FROM Organization LIMIT 1")
print({"org_probe_rows": result["totalSize"]})
```

Do not print connection JSON, token payloads, session IDs, or full exception objects that may include request headers.
