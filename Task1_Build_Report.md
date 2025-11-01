# Task 1 – Build Report (Northstar Assist baseline)

Region `us-east-1`, account 269629487409. All resources were created through the AWS APIs (boto3) – scripts in `scripts/`, raw responses in `evidence/`. No console screenshots exist.

| Component | ID | Evidence |
|---|---|---|
| S3 source bucket (30 docs under `northstar-knowledge-base/`) | `northstar-assist-kb-am6656` | `01_s3_objects.json` |
| Managed Knowledge Base (Titan Embed Text v2) | `U89FCYIR8I`, data source `QAULFCYEWN` | `02_kb.json` |
| Ingestion job | `IJRO7K131N` – 30 scanned, 30 indexed, **0 failed**, status `COMPLETE` | `02_ingestion_job.json` |
| AgentCore Gateway + target `northstar-kb` (exposes `northstar-kb___Retrieve` only) | `northstar-assist-gateway-0x39hcbuob`, target `3ESMLF0W4X` | `03_gateway*.json` |
| AgentCore Harness | `NorthstarAssist-PhZCito2Sx`, model Claude **Sonnet 4.5** (see deviation) | `03_harness_baseline.json` |
| Baseline IAM roles | `NorthstarAssistKBServiceRole`, `NorthstarGatewayServiceRole`, `NorthstarHarnessExecutionRole` | `04_iam_BEFORE.json` |

## Knowledge Base Data Source Sync Verification
The sync completed with zero errors on the full 30-document corpus:
* **Knowledge Base ID:** `U89FCYIR8I`
* **Data Source ID:** `QAULFCYEWN`
* **Ingestion Job ID:** `IJRO7K131N`
* **Status:** `COMPLETE`
* **Statistics:**
  * `numberOfDocumentsScanned`: 30
  * `numberOfNewDocumentsIndexed`: 30
  * `numberOfDocumentsFailed`: 0
  * `numberOfDocumentsDeleted`: 0
  * `numberOfDocumentsSkipped`: 0
* **Evidence File:** `evidence/02_ingestion_job.json`

## Test Transcript: Baseline Harness Retrieval & Response
Below is the verbatim test transcript from the live harness execution recorded in `evidence/05_baseline_hybrid_work.json` (`session_id: northstar-5f01e7038367496d8f53e5a0503eba06`, timestamp `2026-10-18T13:08:47Z`):

```text
================================================================================
USER PROMPT:
What is Northstar's hybrid work policy? Name the source document.
================================================================================

[HARNESS AGENT TRACE: TOOL INVOCATION]
Tool Name: northstar-kb___Retrieve
Tool Use ID: tooluse_Li9n02Gwogc6bdvWZgdK9D
Input Parameters: {"retrievalQuery": {"text": "hybrid work policy"}}

[GATEWAY / KNOWLEDGE BASE TOOL RESULT]
Status: success
Retrieved Document URI: s3://northstar-assist-kb-am6656/northstar-knowledge-base/html/company_policies_handbook.html
Chunk Content:
"Workplace Guidelines Work Schedule Standard Hours: Monday through Friday, 9:00 AM - 6:00 PM local time...
Hybrid Work Policy: Employees may work remotely up to 3 days per week. Minimum 2 days per week in-office (typically Tuesday-Thursday)..."

================================================================================
ASSISTANT RESPONSE (Claude Sonnet 4.5):
Based on the Northstar knowledge base, here is Northstar's **Hybrid Work Policy**:

- **Employees may work remotely up to 3 days per week**
- **Minimum 2 days per week in-office** (typically Tuesday-Thursday)
- **Remote work days should be coordinated** with team/manager
- **Fully remote positions** are available for certain roles (as specified in job description)

**Remote Work Requirements:**
- Reliable high-speed internet connection
- Dedicated, quiet workspace
- Availability during core hours via Slack/email
- Attendance at scheduled video meetings with camera on
- Compliance with information security policies

**Source Document:** `company_policies_handbook.html`
================================================================================
```

This live execution confirms:
1. The harness accepted the user prompt.
2. The agent formulated a semantic retrieval query and invoked the `northstar-kb___Retrieve` tool via the AgentCore Gateway.
3. The Knowledge Base retrieved relevant passages from `company_policies_handbook.html`.
4. Claude Sonnet 4.5 synthesized an accurate response incorporating the retrieved content and citing the exact source document.

## Deviations (disclosed)
* **Model:** Claude Haiku 4.5 returned a Marketplace AccessDenied in the lab account, so Sonnet 4.5 is used.
* **Baseline IAM is reconstructed:** the console's auto-created role policies cannot be reproduced through the API; I created broad console-style policies by hand to represent the "before" state for Task 4 (see that report).
* Built via API, not console; KB application logs were not enabled.
