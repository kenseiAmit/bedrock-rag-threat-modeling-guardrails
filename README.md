# Northstar Assist – Submission Bundle

Author: Amit Kumar Koshta · 2026-10-18

## Contents
| Path | Task |
|---|---|
| `Task1_Build_Report.md` | 1 – build and baseline |
| `ML-BOM_Northstar_Assist.docx` | 2 – ML bill of materials |
| `STRIDE-ML_Northstar_Assist.docx` | 3 – STRIDE-ML threat model |
| `Task4_IAM_Least_Privilege_Report.md` | 4 – IAM scoping and re-test |
| `Task5_Safety_Controls_Report.md` | 5 – guardrail |
| `Task6a_Monitoring_Plan.md`, `Task6b_IR_Playbook.md` | 6 – monitoring and IR |
| `Task7_Launch_Readiness_Report.md` | 7 – edge tests, **approve with conditions** |
| `evidence/` | raw API outputs and logs referenced by the reports |
| `scripts/` | scripts that built and tested everything |
| `MANIFEST.sha256` | SHA-256 of every file |

## Verify
`shasum -a 256 -c MANIFEST.sha256` (run in this folder). Each report cites the evidence file backing each claim.

## Honest disclosures
1. The build was API-driven (boto3); no console screenshots. Evidence is raw API/log output.
2. Model is Claude Sonnet 4.5 (Haiku 4.5 was not accessible in the lab).
3. The "before" IAM roles were reconstructed by me, not the console defaults.
4. Guardrail v2 tuning did not fix the T6 false positive; v1 is attached.
5. Indirect prompt injection via KB content was analysed but not tested empirically.
6. KB application logs and S3 data events were not enabled; Transaction Search was unavailable.
7. ML-BOM reviewer field is unassigned.
8. Evidence contains the lab account ID (269629487409); credentials were scrubbed (checked by grep) and are not included.
9. **All AWS resources were deleted after evidence capture** (see `evidence/99_teardown.json`, `99_teardown_verification.json`); the managed KB `U89FCYIR8I` was confirmed deleted on re-check (ResourceNotFoundException). The system can no longer be queried; re-create with `scripts/`.
