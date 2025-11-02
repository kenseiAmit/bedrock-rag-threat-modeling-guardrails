"""Fill the ML-BOM template (copy) with facts gathered from the live Northstar Assist deployment."""
import docx, copy, json, pathlib
from docx.shared import Pt
W = pathlib.Path(__file__).resolve().parents[1]
SRC = W.parent / "./ML-BOM Template.docx"
OUT = W.parent / "northstar-submission/ML-BOM_Northstar_Assist.docx"
st = json.load(open(W / "evidence/state.json"))
d = docx.Document(SRC)
T = d.tables

def setc(t, r, c, text):
    cell = t.rows[r].cells[c]; cell.text = text

def fill(t, rows, startrow=1):
    for i, vals in enumerate(rows):
        for j, v in enumerate(vals):
            if v is not None: setc(t, startrow + i, j + (1 if len(vals) < len(t.columns) else 0), v)

M = "us.anthropic.claude-sonnet-4-5-20250929-v1:0"
fill(T[0], [("Anthropic Claude Sonnet 4.5 (primary foundation model, via Amazon Bedrock US cross-Region inference profile)",),
  ("20250929 (model ID anthropic.claude-sonnet-4-5-20250929-v1:0; profile " + M + ")",),
  ("text-generation LLM, multimodal input, tool use (agentic reasoning)",),
  ("Anthropic PBC; served by Amazon Web Services (Amazon Bedrock)",),
  ("Proprietary: Anthropic commercial terms / AWS Service Terms (weights not distributed)",),
  ("None executed by the customer. Managed service; framework/runtime libraries are not disclosed by the provider. Harness runtime is AWS-managed (AgentCore). Client side: boto3 1.43.114 (Python 3.12) for build/test scripts.",),
  ("https://aws.amazon.com/bedrock/anthropic/ ; Bedrock model ID anthropic.claude-sonnet-4-5-20250929-v1:0",)])
fill(T[1], [("2026-10-18",), ("Amit Kumar Koshta (AI Security Engineer candidate), with GitHub Copilot assistance",),
  ("Manual inventory from live AWS API output (get_harness, get_knowledge_base, get_gateway, get_guardrail, IAM get_role_policy); no automated SBOM tool exists for managed Bedrock models",)])
fill(T[2], [("https://docs.aws.amazon.com/bedrock/latest/userguide/models-supported.html",), ("https://www.anthropic.com/claude/sonnet",), ("Northstar security team (internal)",)])
d_tags = [p for p in d.paragraphs if p.text.startswith("[Tags or labels")][0]
d_tags.text = "llm, rag, agentic, bedrock, agentcore, harness, claude-sonnet-4-5, titan-embed-text-v2, guardrails, internal-assistant, pii-risk, northstar-assist"
fill(T[3], [("Not disclosed by Anthropic (proprietary pre-training and post-training corpora; provider documentation describes categories only, not itemised datasets)", "n/a", "Proprietary / undisclosed", "TRANSPARENCY GAP: provenance, licensing and PII content of training data cannot be audited by Northstar. Mitigated by guardrails and by grounding answers in the KB."),
  ("Northstar Knowledge Base corpus (30 files: csv, docx, html, pdf, txt, xlsx) in s3://" + st["bucket"] + "/northstar-knowledge-base/", "Northstar Assist internal enterprise corpus (synthetic benchmark data)", "Course materials / internal synthetic", "Retrieval corpus only, not training data. Includes sensitive fixtures (employee directory, customer accounts, infrastructure inventory, financials). Not fine-tuned on.")])
fill(T[4], [("Transformer-based large language model (exact architecture undisclosed)",), ("Claude (Anthropic Claude 4.x family)",)])
fill(T[5], [("Claude Sonnet 4.5 (API-only; no customer-visible parent)", "20250929", "https://aws.amazon.com/bedrock/anthropic/"),
            ("Claude family base model: undisclosed", "n/a", "n/a")], startrow=1)
fill(T[6], [("text (prompt + system prompt + tool results from knowledge base retrieval); up to the harness context limits",),
  ("text (answers, tool-call requests to the gateway Retrieve tool); guardrail-replaced message when blocked",)])
fill(T[7], [("AWS-managed (Bedrock/AgentCore); not customer visible",), ("Amazon Bedrock AgentCore harness runtime (PUBLIC network mode, idle timeout 900s, max lifetime 28800s), AgentCore Gateway, Bedrock Managed Knowledge Base, Bedrock Guardrails",)])
fill(T[8], [("False",), ("None. The harness exposes only the gateway tool northstar-kb___Retrieve (allowedTools = @northstar-assist-gateway). The AgentCore default built-in shell and file_operations tools were observed in the model's toolConfig and removed (see IAM / Safety report).",)])

def para_after(label_text, text):
    for p in d.paragraphs:
        if p.text.startswith(label_text):
            return
    raise KeyError(label_text)
def setp(prefix, text):
    for p in d.paragraphs:
        if p.text.startswith(prefix):
            p.text = text; return
    raise KeyError(prefix)
setp("[Required: Description of how the model should be used]", "Northstar Assist is an internal employee assistant. Authenticated Northstar staff (AWS IAM principals allowed to InvokeHarness) ask questions about company policies, procedures and internal documentation; the model must call the knowledge-base Retrieve tool, answer only from retrieved documents and name its source document.")
setp("[Required: Description of what constitutes out of scope", "x") if False else None
setp("[Required: Description of use cases that are not in scope", "Not for: HR decisions or disclosure of individual compensation/performance data; disclosure of personal contact data or customer contact data in bulk; providing credentials, account IDs or infrastructure identifiers; legal/financial/investment advice; code generation for external targets; autonomous execution of commands (no shell/code tools are enabled); unauthenticated or public-internet use.")
setp("[Required: Description of what constitutes misuse", "Direct prompt injection / jailbreak (e.g. 'ignore your previous instructions'), system-prompt extraction, bulk harvesting of PII or infrastructure details from the KB, indirect injection through poisoned KB documents, attempts to override the approved model or guardrail per request, cost abuse (very large/repeated queries), and use of shared IAM credentials to hide attribution.")

# inventory + overview inserted before "Attestation"
att = [p for p in d.paragraphs if p.text.strip() == "Attestation"][0]
def H(text, style="Heading 2"):
    p = att.insert_paragraph_before(text); 
    try: p.style = d.styles[style]
    except KeyError: pass
    return p
def P(text): return att.insert_paragraph_before(text)
H("4. AI Asset Inventory (system components)", "Heading 1")
P("Each entry lists type, provider, intended use and known limitations / transparency gaps. All identifiers are taken from the live deployment in AWS account 269629487409, region us-east-1.")
inv = [
 ("Foundation model", "Claude Sonnet 4.5 via inference profile " + M, "Anthropic / AWS Bedrock", "Reasoning, tool selection and answer synthesis in the harness.", "Training data and architecture undisclosed; can follow injected instructions; non-deterministic (see launch report). DEVIATION: the lab instructions name Claude Haiku 4.5, but the account returned AccessDenied (AWS Marketplace subscription) for Haiku 4.5; Sonnet 4.5 was the available Anthropic model and was used instead."),
 ("Embedding model", "Amazon Titan Text Embeddings V2 (amazon.titan-embed-text-v2:0)", "Amazon / AWS Bedrock", "Embeds KB documents at ingestion and the query at retrieval time (visible as InvokeModel by the KB role in invocation logs).", "Training data undisclosed; semantic search can surface sensitive chunks for any sufficiently similar query; no per-document access control."),
 ("Knowledge source", "S3 bucket " + st["bucket"] + ", prefix northstar-knowledge-base/ (30 files)", "Customer (Northstar) / AWS S3", "Source-of-truth documents ingested into the KB.", "Contains PII and confidential fixtures; no integrity control on content (a writer could plant instructions: indirect-injection vector). Versioning/Object Lock not enabled in the lab."),
 ("Retrieval service", "Bedrock Managed Knowledge Base " + st["kb_id"] + " (data source " + st["ds_id"] + ", type MANAGED_KNOWLEDGE_BASE_CONNECTOR/S3). Last sync: 30 scanned, 30 indexed, 0 failed.", "AWS Bedrock", "Chunking, embedding, vector storage and Retrieve API.", "Vector store is AWS-managed and opaque (no customer controls over storage/encryption keys); retrieved chunks are not screened by guardrails."),
 ("Orchestration runtime", "AgentCore harness NorthstarAssist (" + st["harness_id"] + ")", "AWS Bedrock AgentCore", "Runs the agent loop: model calls, tool calls, guardrail attachment.", "AWS-managed runtime (PUBLIC network mode). Default built-in shell and file_operations tools are enabled unless allowedTools is restricted (done). Memory disabled."),
 ("Tool gateway", "AgentCore Gateway " + st["gateway_id"] + " with target northstar-kb (bedrock-knowledge-bases connector, Retrieve only)", "AWS Bedrock AgentCore", "Single, IAM-authenticated path from the harness to the KB.", "AWS_IAM inbound auth identifies the harness role, not the end user."),
 ("Safety control", "Bedrock Guardrail " + st["guardrail_id"] + " version 1", "AWS Bedrock", "Screens input and output (prompt-attack, denied topics, PII, harmful content).", "Does not inspect retrieved chunks; topic classification can over-block (legit security-policy question blocked) and is non-deterministic at the edges."),
 ("IAM role", "NorthstarHarnessExecutionRole", "Customer / AWS IAM", "Harness identity: invoke approved model with required guardrail, call the one gateway, write its own logs.", "Baseline was broad; scoped in Task 4. Telemetry actions require Resource * (cannot be resource-scoped)."),
 ("IAM role", "NorthstarGatewayServiceRole", "Customer / AWS IAM", "Gateway identity: GetKnowledgeBase + Retrieve on the one KB.", "Scoped in Task 4."),
 ("IAM role", "NorthstarAssistKBServiceRole", "Customer / AWS IAM", "KB identity: invoke Titan Embed v2 and read the one S3 bucket during sync.", "Not changed; already narrow."),
 ("IAM role", "NorthstarBedrockLoggingRole", "Customer / AWS IAM", "Lets Bedrock write model invocation logs to /northstar-assist/bedrock-invocations.", "Logs contain full prompts and responses (sensitive); restrict log-group access, 30-day retention set."),
]
tb = d.add_table(rows=1, cols=6); tb.style = T[0].style
for i, h in enumerate(["Component type", "Identifier", "Provider", "Intended use", "Limitations / transparency gaps"]): 
    if i < 5: tb.rows[0].cells[i].text = h
tb._tbl.remove(tb.rows[0]._tr) if False else None
for c in tb.rows[0].cells[5:]: pass
# rebuild with 5 columns
tb._tbl.getparent().remove(tb._tbl)
tb = d.add_table(rows=1, cols=5); tb.style = T[0].style
for i, h in enumerate(["Component", "Identifier", "Provider", "Intended use", "Limitations / transparency gaps"]): tb.rows[0].cells[i].text = h
for r in inv:
    cells = tb.add_row().cells
    cells[0].text = r[0]; cells[1].text = r[1]; cells[2].text = r[2]; cells[3].text = r[3]; cells[4].text = r[4]
for row in tb.rows:
    for c in row.cells:
        for p in c.paragraphs:
            for run in p.runs: run.font.size = Pt(8)
att._p.addprevious(tb._tbl)
H("5. System Overview", "Heading 1")
P("An employee sends a question to the AgentCore harness NorthstarAssist (IAM-authenticated InvokeHarness). Before the model sees it, the attached Bedrock Guardrail screens the input (prompt-attack, denied topics, PII). The harness calls Claude Sonnet 4.5 with the Northstar system prompt; the model requests the single enabled tool, northstar-kb___Retrieve, which is served by the AgentCore Gateway. The gateway (using its own scoped IAM role) calls Retrieve on the Managed Knowledge Base, which embeds the query with Titan Text Embeddings V2 and searches the vectors built from the 30 documents in S3. Retrieved chunks return to the model, which writes an answer naming its source document. The guardrail screens the output again (PII, denied topics) before it reaches the user. Every model call is recorded in Bedrock model invocation logs (CloudWatch /northstar-assist/bedrock-invocations) and the harness runtime log group; a metric filter and alarm watch guardrail interventions.")
P("Trust boundaries: user -> harness (IAM), harness -> model (guardrail + IAM deny), harness -> gateway -> KB (separate roles), KB -> S3 (KB role). The KB corpus is treated as untrusted content for injection purposes.")
d.paragraphs  # tables for attestation
for t in d.tables:
    if t.rows[0].cells[0].text == "Role":
        setc(t, 1, 1, "Amit Kumar Koshta"); setc(t, 1, 2, "2026-10-18"); setc(t, 2, 1, "Not yet reviewed (pending instructor/peer review)"); setc(t, 2, 2, "")
d.save(OUT); print("saved", OUT)
