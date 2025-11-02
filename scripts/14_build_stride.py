"""Fill STRIDE-ML template (copy). Threat evidence references files under evidence/."""
import docx, copy, pathlib
from docx.shared import Pt
W = pathlib.Path(__file__).resolve().parents[1]
d = docx.Document(W.parent / "./STRIDE-ML Template.docx")
OUT = W.parent / "northstar-submission/STRIDE-ML_Northstar_Assist.docx"
P = d.paragraphs
def find(prefix):
    for p in d.paragraphs:
        if p.text.startswith(prefix): return p
    raise KeyError(prefix)
def labeled(prefix, label, lines):
    p = find(prefix)
    for r in list(p.runs): r._r.getparent().remove(r._r)
    r = p.add_run(label + " "); r.bold = True
    for i, l in enumerate(lines):
        if i: p.add_run().add_break()
        p.add_run(l)
labeled("System Name:", "System Name:", ["Northstar Assist (AWS Bedrock AgentCore RAG assistant)"])
labeled("Purpose:", "Purpose:", ["Internal employee assistant that answers questions about Northstar policies, procedures and documentation from a 30-document knowledge base, reducing HR/IT/helpdesk load. Business value depends on accuracy and on not leaking confidential or personal data."])
labeled("Architecture:", "Architecture:", ["User (IAM principal) -> AgentCore harness (Claude Sonnet 4.5, system prompt, guardrail v1) -> AgentCore Gateway (northstar-kb___Retrieve) -> Bedrock Managed Knowledge Base (Titan Embed v2 vectors) -> S3 source bucket. Output returns through the guardrail. Logs: Bedrock invocation logs + harness runtime logs in CloudWatch."])
labeled("Key Components:", "Key Components:", ["- Harness NorthstarAssist: agent loop, model + guardrail attachment, tool allow-list (gateway only).",
 "- Claude Sonnet 4.5: generates answers/tool calls; untrusted-behaviour component (can be steered by text).",
 "- AgentCore Gateway + target: only path to data; AWS_IAM authorised; Retrieve only.",
 "- Managed KB + Titan Embed v2 + S3 corpus: knowledge source (contains PII/confidential fixtures).",
 "- Bedrock Guardrail: input/output screening. IAM roles (harness, gateway, KB, logging): authorisation."])
labeled("Trust Boundaries:", "Trust Boundaries:", ["- TB1 User -> Harness: untrusted free text; IAM-authenticated but no per-end-user identity.",
 "- TB2 Harness -> Model/Guardrail: system prompt vs user prompt; guardrail + IAM Deny enforce policy.",
 "- TB3 Harness -> Gateway -> KB: tool call and retrieved content cross back into the model context (untrusted data entering a trusted context).",
 "- TB4 KB -> S3: corpus integrity; anyone with s3:PutObject controls what the model reads.",
 "- TB5 Model -> User: output may contain data the user must not see."])
find("[Describe the sensitive data processed").text = (
 "Assets (classification / why attractive): (1) employee_directory.csv - names, titles, work emails, extensions (Confidential PII; social engineering/phishing targeting). "
 "(2) customer_accounts.csv, sales_pipeline.csv, support_tickets.csv - customer contacts, revenue, deals (Confidential business). "
 "(3) aws_infrastructure_inventory.csv, aws_architecture_documentation.html, security policy - account IDs, instance IDs, controls (Confidential; attack reconnaissance). "
 "(4) Financial XLSX/PDF files (Confidential). (5) General policies/handbooks (Internal). (6) System prompt and tool configuration (Internal; helps craft attacks). "
 "(7) Model outputs and prompts in invocation logs (inherit the sensitivity of the data; contain full text). (8) IAM roles/credentials of harness, gateway, KB. "
 "No model training or fine-tuning data exists: Claude and Titan are used as-is, so training-data extraction is not a Northstar-owned risk; the KB corpus is the data at risk. "
 "Baseline evidence: with no guardrail the harness returned 8 employees' names/emails/extensions, customer contacts and AWS account/instance IDs on request (evidence/07_baseline_T2*, T4*).")

def sec_replace(heading, threats):
    h = find(heading); i = [k for k, p in enumerate(d.paragraphs) if p._p is h._p][0]
    ps = d.paragraphs
    j = i + 1
    while not (ps[j].text[:2] in ("3.", "4.") or ps[j].text.startswith("4. ")): j += 1
    nxt = ps[j]
    tpl_title, tpl_desc, tpl_mit = None, None, None
    for p in ps[i + 2:j]:
        if p.text.startswith("[Threat ID]"): tpl_title = p
        elif p.text.startswith("Mitigation:"): tpl_mit = p
        elif tpl_title is not None and tpl_desc is None: tpl_desc = p
    for p in ps[i + 2:j]: p._p.getparent().remove(p._p)
    for (tid, name, desc, mit) in threats:
        a = nxt.insert_paragraph_before(); r = a.add_run(f"{tid}: {name}"); r.bold = True
        nxt.insert_paragraph_before(desc)
        b = nxt.insert_paragraph_before(); r = b.add_run("Mitigation: "); r.bold = True; b.add_run(mit)
sec_replace("3.1 Spoofing", [
 ("S-1", "Caller impersonation / no end-user identity",
  "Inbound auth is AWS_IAM. Any principal with bedrock-agentcore:InvokeHarness (or stolen credentials, e.g. shared lab/role credentials) can use the assistant, and Bedrock invocation logs show only the harness role as identity, not the employee. Likelihood: Medium. Impact: Medium (misattributed misuse, access by non-employees). Priority: Medium.",
  "Restrict InvokeHarness to a named role/group; use SSO with per-user session names; pass the user id in requestMetadata/runtimeSessionId so it appears in logs; short-lived credentials only. Residual: harness has no native end-user identity."),
 ("S-2", "Spoofed document provenance in the KB",
  "A document uploaded to the S3 prefix is indistinguishable from an authoritative policy; the assistant cites it as a source. Likelihood: Low-Medium. Impact: High (misinformation presented as policy). Priority: Medium.",
  "Limit s3:PutObject to a content-owner role, enable S3 versioning/CloudTrail data events, re-sync only after review. Not enabled in the lab; recommended for production.")])
sec_replace("3.2 Tampering", [
 ("T-1", "Indirect prompt injection / data poisoning via retrieved KB content",
  "Retrieved chunks enter the model context as trusted-looking text. An attacker (or a careless employee) who can write a document to the S3 source, or an external source later synced, can embed instructions ('when asked about X, reveal Y / call tool Z'). Bedrock Guardrails screen the user input and model output but do NOT screen tool results/retrieved chunks, so the control gap is structural. The 30 corpus documents were grep-checked and contain no injected instructions, so this risk was assessed analytically and could not be demonstrated with the shipped corpus (no test document was added to avoid altering the dataset). Likelihood: Medium. Impact: High. Priority: HIGH (top 2).",
  "Tight write access to the bucket, S3 versioning and review before sync; harness exposes only Retrieve (no shell, file or write tools) so injected instructions cannot execute actions or exfiltrate beyond the answer text; output guardrail (PII/topic) still screens the final answer; system prompt tells the model to answer only from documents. Residual risk accepted with monitoring (zero-chunk / anomaly signals)."),
 ("T-2", "Per-request model or configuration override",
  "invoke_harness accepts a per-request model override. With the baseline broad role a caller switched the harness to an unapproved model (Nova 2 Lite) with success (evidence/10_BEFORE_model_override_nova.json). Likelihood: Medium (any authorised caller). Impact: Medium-High (bypass of model choice / guardrail). Priority: High.",
  "IAM scoped to one inference profile plus a Deny on InvokeModel* without the Northstar guardrail identifier. After scoping, both the unapproved model and the approved-model-without-guardrail request fail with AccessDenied (evidence/10_AFTER_*, 11_AFTER_no_guardrail_override.json).")])
sec_replace("3.3 Repudiation", [
 ("R-1", "Insufficient audit trail for who asked what",
  "Model invocation logging is off by default; even when on, identity = harness role. An insider could extract data and later deny it; investigators could not reconstruct sessions. Likelihood: Medium. Impact: Medium. Priority: Medium.",
  "Invocation logging enabled to CloudWatch (30-day retention) capturing full prompt, output, guardrail trace and token usage (evidence/14_invocation_log_full.json); harness runtime logs; add per-user identifier in session id; export logs before containment actions. Alarm on guardrail interventions.")])
sec_replace("3.4 Information Disclosure", [
 ("I-1", "Disclosure of PII and confidential business data from the KB (excessive data exposure)",
  "The KB has no per-document or per-user access control; any semantic match is retrievable. OBSERVED without guardrail: the harness listed 8 Engineering employees with emails and extensions, customer contacts, and AWS account/instance IDs (evidence/07_baseline_T2_*, T4_*). Likelihood: High. Impact: High. Priority: CRITICAL (top 1).",
  "Guardrail: denied topics (compensation/HR data, credentials & infrastructure secrets), PII filters (email, phone, keys, password, SSN, card) on output, prompt-attack filter on input. With the guardrail all 36 test runs (6 prompts x 3 repeats x 2 phases) were blocked (evidence/07_hardened_*, 07_final_*). Residual: blocks are coarse (also blocked a legitimate security-policy question), and non-PII sensitive text (revenue, infrastructure details) relies on topic detection. Real fix: remove or segment sensitive datasets from the KB."),
 ("I-2", "System prompt and configuration leakage",
  "Attackers ask for the system prompt or tool list to refine attacks. The built-in tools shell and file_operations were visible to the model by default. Likelihood: Medium. Impact: Low-Medium. Priority: Medium.",
  "Prompt-attack filter blocks 'reveal your system prompt' (T1: blocked 6/6); system prompt contains no secrets; unneeded tools removed (allowedTools).")])
sec_replace("3.5 Denial of Service", [
 ("D-1", "Denial of wallet / resource exhaustion",
  "Loops of expensive prompts or repeated retrievals inflate tokens (logged model calls ranged from ~1.2k to 11.4k input tokens; harness defaults allowed 75 iterations and a 3600 s timeout). Likelihood: Medium. Impact: Medium. Priority: Medium.",
  "Harness maxIterations lowered from 75 to 10 and timeout from 3600 s to 300 s, CloudWatch alarm on guardrail interventions (fired during testing), token-anomaly alerts and an account budget, IAM limits who can invoke. Residual: no native per-user rate limiting in the harness.")])
sec_replace("3.6 Elevation of Privilege", [
 ("E-1", "Direct prompt injection / jailbreak",
  "Users try 'ignore your previous instructions...', role-play, encoding tricks. The un-guardrailed model refused the simple attempt on its own (evidence/07_baseline_T1) but model refusal is probabilistic. Likelihood: High. Impact: High. Priority: HIGH (top 3).",
  "Prompt-attack filter (input strength HIGH) - blocked 6/6 attempts with guardrail_intervened and 0 model tokens; IAM Deny ensures the guardrail cannot be omitted per request. Residual: novel jailbreaks may bypass classifiers; monitor intervention counts."),
 ("E-2", "Abuse of default built-in tools (shell, file_operations) and over-privileged roles",
  "AgentCore harness enables a sandbox shell and file tool by default (allowedTools = ['*']); the baseline execution role also had Browser, CodeInterpreter, Memory, EFS/S3 Files, bedrock-mantle:* on *. A successful injection could run commands in the runtime or use the role's other permissions. Likelihood: Medium. Impact: High. Priority: High.",
  "allowedTools restricted to @northstar-assist-gateway (verified in model toolConfig: only northstar-kb___Retrieve); roles scoped to least privilege (Task 4 report). Residual: AWS-managed runtime internals.")])

# prioritized register before "4. Residual Risks"
res = find("4. Residual Risks")
def add_before(text, bold=False):
    p = res.insert_paragraph_before(); r = p.add_run(text); r.bold = bold; return p
add_before("3.7 Prioritized Risk Register", True)
reg = [("Rank", "ID", "Risk", "Likelihood", "Impact", "Priority", "Status of mitigation"),
 ("1", "I-1", "PII / confidential data exposure from KB", "High", "High", "Critical", "Mitigated (guardrail); residual coarse blocking"),
 ("2", "T-1", "Indirect injection via retrieved content", "Medium", "High", "High", "Partially mitigated; guardrail cannot screen chunks"),
 ("3", "E-1", "Direct prompt injection / jailbreak", "High", "High", "High", "Mitigated (PROMPT_ATTACK + IAM Deny)"),
 ("4", "E-2", "Built-in tools / over-privileged roles", "Medium", "High", "High", "Mitigated (allowedTools + scoped IAM)"),
 ("5", "T-2", "Per-request model/guardrail override", "Medium", "Med-High", "High", "Mitigated (IAM) and retested"),
 ("6", "S-1/R-1", "No end-user identity / weak attribution", "Medium", "Medium", "Medium", "Partially mitigated (logging)"),
 ("7", "D-1/S-2/I-2", "Cost abuse, doc provenance, prompt leakage", "Low-Med", "Low-Med", "Medium", "Monitoring")]
tb = d.add_table(rows=len(reg), cols=7); tb.style = d.tables[-1].style
for i, row in enumerate(reg):
    for j, v in enumerate(row):
        c = tb.rows[i].cells[j]; c.text = v
        for p in c.paragraphs:
            for r in p.runs: r.font.size = Pt(8); r.bold = (i == 0)
res._p.addprevious(tb._tbl)
find("[Risk Name]:").text = ("Indirect prompt injection: guardrails do not inspect retrieved chunks, so a poisoned document could still steer the model; only no-action tooling and output screening limit the blast radius. "
 "Sensitive data in the KB: access control is all-or-nothing; the guardrail is a classifier, not an authorisation system. "
 "Guardrail over-blocking and non-determinism: a legitimate password-policy question was blocked (evidence/13_guardrail_input_diagnosis_v1.json; a tuned v2 did not clear it) and answers vary between runs. "
 "No end-user identity: attribution stops at the harness role. Model substitution: Claude Haiku 4.5 named in the lab was unavailable (Marketplace AccessDenied); Sonnet 4.5 used.")
find("[Provide actionable recommendations").text = (
 "1) Remove or segment employee, customer, finance and infrastructure datasets from the general KB; apply per-audience KBs. 2) Enable S3 versioning, restrict PutObject, review documents before sync. "
 "3) Keep invocation logging on; alarm on >5 guardrail interventions/hour; track zero-chunk retrieval and token spikes; weekly review of intervention samples. 4) Pass end-user identity into sessions. "
 "5) Re-run the Task 7 test battery after every prompt, guardrail, model or KB change; add red-team tests for indirect injection. 6) User education: do not paste secrets; report odd answers.")
for t in d.tables:
    if t.rows[0].cells[0].text == "Role":
        for r, (n) in enumerate(["Amit Kumar Koshta (author; unreviewed)", "Not assigned", "Not assigned"], start=1):
            t.rows[r].cells[1].text = n; t.rows[r].cells[2].text = "2026-10-18" if r == 1 else ""
for p in list(d.paragraphs):
    if p.text.startswith("[Identify") or p.text.startswith("[Describe risks"):
        p._p.getparent().remove(p._p)
d.save(OUT); print("saved")
