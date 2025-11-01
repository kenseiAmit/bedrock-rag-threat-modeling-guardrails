# Task 6 – Monitoring Plan (Northstar Assist)

Author: Amit Kumar Koshta · Date: 2026-10-18 · System: Northstar Assist (AgentCore harness `NorthstarAssist-PhZCito2Sx` → Gateway → Managed KB `U89FCYIR8I`, guardrail `cbrljxvgh2rc` v1)

What is **actually deployed** vs **recommended** is marked in each row. Deployed items were created by `scripts/08_monitoring.py` and exercised with the real test traffic.

## 1. Log and metric sources

| # | Source | What to log (fields that reconstruct an incident) | Alert / review condition | State |
|---|---|---|---|---|
| 1 | **Bedrock model invocation logs** → CloudWatch `/northstar-assist/bedrock-invocations` (30-day retention, role `NorthstarBedrockLoggingRole`). Harness calls appear as `ConverseStream` with `identity.arn = …assumed-role/NorthstarHarnessExecutionRole/BedrockAgentCore-<session-uuid>`; KB embedding calls appear as `InvokeModel` by `NorthstarAssistKBServiceRole`. | `timestamp`, `requestId`, `identity.arn` (one session id per harness session), `modelId`, full `input.inputBodyJson` (user prompt, system prompt, `toolConfig` tool list, prior tool results), `output.outputBodyJson` (answer, `stopReason`, `usage.inputTokens/outputTokens/totalTokens`, `trace.guardrail.inputAssessment/outputAssessments` with policy type, filter, confidence, `action`) | (a) **Guardrail interventions > 5 per hour** (CloudWatch alarm below). (b) `modelId` ≠ `us.anthropic.claude-sonnet-4-5-20250929-v1:0` on a harness identity → model override attempt (also denied by IAM). (c) `toolConfig` lists any tool other than `northstar-kb___Retrieve` → configuration drift. | **Deployed** (53 entries captured: `evidence/14_invocation_log_full.json`) |
| 2 | **Guardrail interventions (AI-specific)** – derived from source 1 (`stopReason = guardrail_intervened`, `trace.guardrail…filters[].type`, `topics[].name`, `piiEntities[].type`). Bedrock/Guardrails CloudWatch metrics (`AWS/Bedrock/Guardrails InvocationsIntervened`) should also be checked in production; in this lab the log-derived metric is the one verified. | count per hour, per policy (`PROMPT_ATTACK`, topic name, PII type), per session id, input vs output side | **Concrete alert:** metric `NorthstarAssist/GuardrailIntervened` Sum **> 5 in 1 hour** → alarm `NorthstarAssist-GuardrailInterventions-High` (SNS in production). Tighter investigation trigger: **> 5 `PROMPT_ATTACK` interventions in 1 hour from one `identity.arn` session** (Insights query Q4/Q2). | **Deployed** – the alarm went to **ALARM** during testing (40 interventions in the 13:00 hour vs threshold 5; `evidence/18_monitoring_state.json`) |
| 3 | **Retrieval anomalies (AI-specific)** – harness runtime log group `/aws/bedrock-agentcore/runtimes/harness_NorthstarAssist-88mkHp4jsF-DEFAULT` and tool results inside source 1. | per request: was `northstar-kb___Retrieve` called, number of `retrievalResults`, top `score`, `documentId` (S3 URI) of each chunk | (a) Answer produced with **no Retrieve tool call** (model answering from its own knowledge) > 3 per hour; (b) a Retrieve result with `"retrievalResults":[]` (zero chunks) followed by a confident answer; (c) **sensitive source documents** (`employee_directory.csv`, `customer_accounts.csv`, `aws_infrastructure_inventory.csv`) retrieved > 10 times per hour. Query Q5 detects (b). | Query tested (0 zero-chunk results in test window); alarm **recommended** |
| 4 | **Token-count anomalies (AI-specific)** – source 1 `usage.totalTokens`. Observed normal range 1.2k–4.4k per call; retrieval-heavy answers 8–11k. | tokens per request and per session | Any request **> 3× the session average or > 12k tokens**, or one session > 50k tokens/hour (cost abuse, prompt stuffing, loops). Query Q3. | Query tested; alarm **recommended**. Harness limits: `maxIterations 10`, `timeoutSeconds 300`. |
| 5 | **S3 access/data events for the KB source bucket** `northstar-assist-kb-am6656` | `PutObject/DeleteObject/PutBucketPolicy` by principal, ETag, time; KB sync (`StartIngestionJob`) events | Any `PutObject` to `northstar-knowledge-base/` by a principal other than the content-owner role, or a sync started after an unreviewed write (indirect-injection / poisoning vector) | **Recommended** (not enabled in the lab: CloudTrail data events + S3 versioning) |
| 6 | **KB application logs** `/aws/vendedlogs/bedrock/knowledge-base/APPLICATION_LOGS/U89FCYIR8I` | ingestion failures, document-level errors | Ingestion job with `numberOfDocumentsFailed > 0` | **Not deployed** (log group does not exist; sync results were verified through the `get_ingestion_job` API: 30 scanned/30 indexed/0 failed) |
| 7 | **CloudWatch cost alarms / AWS Budgets** | daily Bedrock spend, tokens | Daily spend > 2× trailing 7-day average | **Recommended** |
| 8 | **CloudTrail management events** | `InvokeHarness`, IAM policy changes on the two roles, `UpdateHarness`, `UpdateGuardrail` | Any change to harness/guardrail/role policies outside change windows | **Recommended** (Cloud Lab trail not under our control) |

Not available in the Cloud Lab: CloudWatch GenAI Observability traces (Transaction Search).

## 2. Deployed alert (concrete)

```
Metric filter  NorthstarGuardrailIntervened  on /northstar-assist/bedrock-invocations
  pattern: "guardrail_intervened"   → NorthstarAssist/GuardrailIntervened (value 1, default 0)
Alarm          NorthstarAssist-GuardrailInterventions-High
  Sum > 5 over 3600 s, 1 evaluation period, TreatMissingData=notBreaching
```
The filter is account-wide (all sessions). Per-session attribution is done with the Logs Insights queries below (each harness session has its own `BedrockAgentCore-<uuid>` role session name). Limitation: it counts input-side and output-side blocks together and fires on benign over-blocks too.

## 3. Logs Insights queries (all executed – results in `evidence/19_insights_queries.json`)

```
# Q1 interventions per hour           → 40 in the test hour
filter output.outputBodyJson.stopReason = "guardrail_intervened" | stats count() as interventions by bin(1h)
# Q2 which filter fired               → PROMPT_ATTACK 8, MISCONDUCT 6, others (topic/PII)
filter output.outputBodyJson.stopReason = "guardrail_intervened"
| parse @message /"filters":\[\{"type":"(?<attack>[A-Z_]+)"/ | stats count() by attack
# Q3 token anomalies                  → max 11,434 tokens
filter output.outputBodyJson.usage.totalTokens > 8000 | fields @timestamp, requestId, output.outputBodyJson.usage.totalTokens as tokens | sort tokens desc | limit 10
# Q4 calls and tokens per session     (per-session attack hunting; add the stopReason filter for interventions)
stats count() as calls, sum(output.outputBodyJson.usage.totalTokens) as tokens by identity.arn, modelId
# Q5 zero-chunk retrieval             → 0 in the test window
filter @message like /\"retrievalResults\\\":\[\]/ | stats count() as zero_chunk_results
```

## 4. Reflection

**Which source is most unique to AI systems?** Guardrail interventions in the model invocation logs (source 2). A web-app plan has no equivalent of "the content of the request was judged adversarial". It is a direct, early measure of attack pressure, and each record names the policy and confidence, e.g. `PROMPT_ATTACK HIGH → BLOCKED` (seen in this lab). Retrieval and token anomalies are the next most AI-specific signals.

**What could go wrong that none of these sources would catch?**
1. A **successful indirect injection** or data poisoning: nothing is blocked, the answer is simply wrong or subtly steered, and guardrails do not inspect retrieved chunks.
2. **Sensitive data legitimately retrievable** by anyone with access (no per-user authorisation) – the logs show a normal request.
3. **Slow, low-volume extraction** below the thresholds (a few queries per day), or paraphrases that the classifier does not recognise.
4. **Attribution gaps:** identity is the harness session, not the employee, unless user ids are added to sessions.
5. A **silent logging failure** or someone disabling invocation logging (needs CloudTrail alert on `DeleteModelInvocationLoggingConfiguration`).
6. **Hallucinations** that cite real documents – quality monitoring (sampling and human review) is needed.
