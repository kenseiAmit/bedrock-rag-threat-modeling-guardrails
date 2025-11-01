# Task 6 – Incident Response Playbook (Northstar Assist)

Author: Amit Kumar Koshta · Date: 2026-10-18 · Scenario: **sustained prompt-injection / data-extraction attempt** (alarm `NorthstarAssist-GuardrailInterventions-High`: > 5 guardrail interventions per hour). Commands use real resource IDs from this deployment (`us-east-1`).

## 1. Detection signals
| Signal | Source | Meaning |
|---|---|---|
| Alarm `NorthstarAssist-GuardrailInterventions-High` in ALARM | CloudWatch (monitoring plan #2) | Attack pressure or over-blocking spike |
| `PROMPT_ATTACK` repeated from one `BedrockAgentCore-<uuid>` session | Insights Q2/Q4 | Targeted attacker/user |
| Answers without Retrieve, zero-chunk retrievals, sensitive files retrieved often | Monitoring #3 | Probing or poisoning |
| Token spike > 12k per request | Monitoring #4 | Cost abuse |
| `modelId` or `toolConfig` differs from baseline | Invocation log | Config drift / bypass attempt |

## 2. Roles
Incident commander (security on-call) · AWS operator (runs containment) · Data owner (HR/Finance – judges exposure) · Comms/Legal (employee/customer notification) · Scribe.

## 3. First 15 minutes – triage and containment
1. **Acknowledge** alarm; open a ticket; note start time.
2. **Scope** (read-only):
```
aws logs start-query --log-group-name /northstar-assist/bedrock-invocations --start-time $(date -v-1H +%s) --end-time $(date +%s) \
 --query-string 'filter output.outputBodyJson.stopReason = "guardrail_intervened" | stats count() by identity.arn'
```
3. **Did anything get through?** Look for `stopReason != guardrail_intervened` records from the same session whose output contains emails/IDs/salaries (Q4 + `filter @message like /@northstar/`).
4. **Contain, least disruptive first:**
   - *Tighten guardrail* (already in force): confirm harness still has `guardrailConfig` for `cbrljxvgh2rc` (`aws bedrock-agentcore-control get-harness --harness-id NorthstarAssist-PhZCito2Sx`).
   - *Throttle/limit*: `update-harness … --max-iterations 3 --timeout-seconds 60`.
   - *Cut off a source*: if one caller identity is identified, add an explicit Deny for that principal on `bedrock-agentcore:InvokeHarness`.
   - *Full stop (kill switch)*: attach an inline `Deny bedrock-agentcore:InvokeHarness` / `bedrock:InvokeModel*` policy to the calling role, or `aws bedrock-agentcore-control delete-gateway-target` to remove the KB tool. Decision point: use the kill switch if **any** sensitive data appears in an answer (not merely blocked).
5. **Preserve evidence**: export the log window (`aws logs filter-log-events … > incident-<id>.json`), record guardrail version and harness config. Do **not** delete logs; retention is 30 days.

## 4. First hour – investigation
- Reconstruct the session: all requests for the session's `identity.arn`, prompts (`input.inputBodyJson`), tool calls, retrieved `documentId`s, outputs.
- Classify: (a) blocked attempts only → no data impact; (b) allowed output with sensitive data → **data incident**; (c) config/IAM change → check CloudTrail (`UpdateHarness`, `PutRolePolicy`, `UpdateGuardrail`).
- Check KB integrity: S3 `ListObjectVersions` / CloudTrail S3 events for unexpected writes to `northstar-knowledge-base/`; compare against the 30 known documents (sync was 30/30). A poisoned document means: remove it, re-sync (`start-ingestion-job`), review all answers since the last sync.
- Check for false positives: legitimate questions (e.g. password-policy – known over-block T6) can trip the alarm. Review prompts before blaming a user.
- Check cost: token totals via Q4.

## 5. Escalation
| Condition | Escalate to |
|---|---|
| Only blocked attempts, single user | Manager/HR (policy violation) |
| Any PII, salary, customer or infra data in a delivered answer | CISO + data owner + Legal/privacy (breach assessment, notification clocks) |
| KB poisoning / IAM change | CISO + platform owner; treat as security compromise |
| Credentials appear anywhere | Rotate immediately (cloud security) |

## 6. Recovery
1. Remove the root cause (revoke user/access, delete poisoned doc, restore config via the scripts in `scripts/`).
2. Re-run the edge-test battery `scripts/06_edge_tests.py` (T1–T6) and the benign sanity query; require all attacks blocked and the benign hybrid-work question answered.
3. Lift containment in reverse order; keep the alarm and raise monitoring for 7 days.

## 7. Post-incident review (within 5 days)
Timeline; detection delay (alarm period is 1 h → consider 5 min); what was exposed; which control worked or failed; actions: guardrail tuning (new denied-topic examples), KB data minimisation, add user identity to sessions, S3 write restrictions, update thresholds and this playbook. Track actions to closure.

## 8. Known gaps affecting response
No KB application logs; no per-employee identity in logs; alarm is account-wide without SNS in the lab; Transaction Search unavailable; indirect injection through KB content cannot be detected by guardrails and would show no alarm – periodic document review and S3 write monitoring are the compensating controls.
