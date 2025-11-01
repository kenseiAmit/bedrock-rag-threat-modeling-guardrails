"""Task 1b: baseline roles, AgentCore Gateway + KB target, and the harness (no guardrail yet)."""
import json, time, pathlib, boto3

W = pathlib.Path(__file__).resolve().parents[1]
EV = W / "evidence"
st = json.load(open(EV / "state.json"))
region = "us-east-1"
acct = boto3.client("sts").get_caller_identity()["Account"]
iam = boto3.client("iam")
ac = boto3.client("bedrock-agentcore-control", region_name=region)
kb_id = st["kb_id"]
MODEL_ID = "us.anthropic.claude-haiku-4-5-20251001-v1:0"

SYSTEM_PROMPT = (
    "You are Northstar Assist, Northstar Technologies' internal employee assistant. Your job is to help "
    "Northstar employees find accurate answers to questions about company policies, procedures, and internal "
    "documentation. Always search the Northstar knowledge base tool before answering a question about "
    "Northstar. Base your answers only on the retrieved documents and name the source document you used. "
    "Do not make up details. If the knowledge base does not contain relevant information, say so clearly. "
    "Do not guess. Do not discuss topics unrelated to Northstar operations."
)


def trust(svc):
    return json.dumps({"Version": "2012-10-17", "Statement": [{
        "Effect": "Allow", "Principal": {"Service": svc}, "Action": "sts:AssumeRole",
        "Condition": {"StringEquals": {"aws:SourceAccount": acct}}}]})


def role(name, svc, desc, policies):
    try:
        r = iam.create_role(RoleName=name, AssumeRolePolicyDocument=trust(svc), Description=desc)["Role"]
    except iam.exceptions.EntityAlreadyExistsException:
        r = iam.get_role(RoleName=name)["Role"]
    for pn, doc in policies.items():
        iam.put_role_policy(RoleName=name, PolicyName=pn, PolicyDocument=json.dumps(doc))
    return r["Arn"]


GW_BASELINE = {"Version": "2012-10-17", "Statement": [
    {"Sid": "RetrieveFromKB", "Effect": "Allow", "Action": ["bedrock:GetKnowledgeBase", "bedrock:Retrieve"],
     "Resource": f"arn:aws:bedrock:{region}:{acct}:knowledge-base/{kb_id}"},
    {"Sid": "AgenticAndRerank", "Effect": "Allow", "Action": ["bedrock:AgenticRetrieveStream", "bedrock:Rerank"], "Resource": "*"},
    {"Sid": "InvokeAnyModel", "Effect": "Allow",
     "Action": ["bedrock:InvokeModel", "bedrock:InvokeModelWithResponseStream", "bedrock:GetInferenceProfile"],
     "Resource": ["arn:aws:bedrock:*::foundation-model/*", f"arn:aws:bedrock:*:{acct}:*"]},
    {"Sid": "ApplyAnyGuardrail", "Effect": "Allow", "Action": "bedrock:ApplyGuardrail",
     "Resource": f"arn:aws:bedrock:{region}:{acct}:guardrail/*"},
    {"Sid": "GatewayRead", "Effect": "Allow", "Action": "bedrock-agentcore:GetGateway",
     "Resource": f"arn:aws:bedrock-agentcore:{region}:{acct}:gateway/*"},
]}
gw_role = role("NorthstarGatewayServiceRole", "bedrock-agentcore.amazonaws.com",
               "Northstar gateway service role (baseline, console-default-style broad permissions)",
               {"GatewayBaselinePolicy": GW_BASELINE})
time.sleep(10)

gw = ac.create_gateway(name="northstar-assist-gateway", roleArn=gw_role, protocolType="MCP",
                       authorizerType="AWS_IAM",
                       description="Exposes the Northstar managed knowledge base to the harness")
gw_id = gw["gatewayId"]
while True:
    g = ac.get_gateway(gatewayIdentifier=gw_id)
    print("gateway", g["status"])
    if g["status"] not in ("CREATING", "UPDATING"):
        break
    time.sleep(8)
assert g["status"] == "READY", g

tgt = ac.create_gateway_target(
    gatewayIdentifier=gw_id, name="northstar-kb",
    description="Search Northstar Technologies internal documents (policies, procedures, reports, "
                "spreadsheets) and return relevant passages with source documents.",
    targetConfiguration={"mcp": {"connector": {
        "source": {"connectorId": "bedrock-knowledge-bases"},
        "configurations": [{"name": "Retrieve", "parameterValues": {"knowledgeBaseId": kb_id}}]}}},
    credentialProviderConfigurations=[{"credentialProviderType": "GATEWAY_IAM_ROLE"}])
tid = tgt["targetId"]
while True:
    t = ac.get_gateway_target(gatewayIdentifier=gw_id, targetId=tid)
    print("target", t["status"], t.get("statusReasons"))
    if t["status"] not in ("CREATING", "UPDATING"):
        break
    time.sleep(8)
assert t["status"] == "READY", t
json.dump(g, open(EV / "03_gateway.json", "w"), indent=1, default=str)
json.dump(t, open(EV / "03_gateway_target.json", "w"), indent=1, default=str)

HARNESS_BASELINE = {"Version": "2012-10-17", "Statement": [
    {"Sid": "InvokeAnyFoundationModel", "Effect": "Allow",
     "Action": ["bedrock:InvokeModel", "bedrock:InvokeModelWithResponseStream"],
     "Resource": ["arn:aws:bedrock:*::foundation-model/*", f"arn:aws:bedrock:*:{acct}:*"]},
    {"Sid": "InvokeGateways", "Effect": "Allow", "Action": "bedrock-agentcore:InvokeGateway",
     "Resource": f"arn:aws:bedrock-agentcore:{region}:{acct}:gateway/*"},
    {"Sid": "BrowserAndCodeInterpreter", "Effect": "Allow",
     "Action": ["bedrock-agentcore:*Browser*", "bedrock-agentcore:*CodeInterpreter*"], "Resource": "*"},
    {"Sid": "MemoryAccess", "Effect": "Allow", "Action": "bedrock-agentcore:*Memory*", "Resource": "*"},
    {"Sid": "FileSystemMounts", "Effect": "Allow",
     "Action": ["elasticfilesystem:ClientMount", "elasticfilesystem:ClientWrite", "s3files:*"], "Resource": "*"},
    {"Sid": "MantleAndMetrics", "Effect": "Allow", "Action": ["bedrock-mantle:*", "cloudwatch:PutMetricData"], "Resource": "*"},
    {"Sid": "RuntimeLogs", "Effect": "Allow",
     "Action": ["logs:CreateLogGroup", "logs:DescribeLogStreams", "logs:CreateLogStream", "logs:PutLogEvents"],
     "Resource": f"arn:aws:logs:{region}:{acct}:log-group:/aws/bedrock-agentcore/runtimes/*"},
    {"Sid": "RuntimeImageAndTelemetry", "Effect": "Allow",
     "Action": ["ecr-public:GetAuthorizationToken", "ecr:GetAuthorizationToken", "sts:GetServiceBearerToken",
                "xray:PutTraceSegments", "xray:PutTelemetryRecords"], "Resource": "*"},
    {"Sid": "RuntimeManagedImagePull", "Effect": "Allow",
     "Action": ["ecr:BatchGetImage", "ecr:GetDownloadUrlForLayer", "ecr:BatchCheckLayerAvailability"],
     "Resource": f"arn:aws:ecr:{region}:*:repository/harness-*"},
    {"Sid": "WorkloadIdentity", "Effect": "Allow",
     "Action": ["bedrock-agentcore:GetWorkloadAccessToken", "bedrock-agentcore:GetWorkloadAccessTokenForJWT"],
     "Resource": [f"arn:aws:bedrock-agentcore:{region}:{acct}:workload-identity-directory/default",
                  f"arn:aws:bedrock-agentcore:{region}:{acct}:workload-identity-directory/default/workload-identity/*"]},
]}
h_role = role("NorthstarHarnessExecutionRole", "bedrock-agentcore.amazonaws.com",
              "Northstar harness execution role (baseline, console-default-style broad permissions)",
              {"HarnessBaselinePolicy": HARNESS_BASELINE})
time.sleep(10)

h = ac.create_harness(
    harnessName="NorthstarAssist", executionRoleArn=h_role,
    model={"bedrockModelConfig": {"modelId": MODEL_ID, "apiFormat": "converse_stream"}},
    systemPrompt=[{"text": SYSTEM_PROMPT}],
    tools=[{"type": "agentcore_gateway", "name": "northstar-assist-gateway",
            "config": {"agentCoreGateway": {"gatewayArn": g["gatewayArn"], "outboundAuth": {"awsIam": {}}}}}],
    memory={"disabled": {}},
)["harness"]
hid = h["harnessId"]
while True:
    hh = ac.get_harness(harnessId=hid)["harness"]
    print("harness", hh["status"])
    if hh["status"] not in ("CREATING", "UPDATING"):
        break
    time.sleep(10)
json.dump(hh, open(EV / "03_harness_baseline.json", "w"), indent=1, default=str)
st.update({"gateway_id": gw_id, "gateway_arn": g["gatewayArn"], "gateway_role": gw_role, "target_id": tid,
           "harness_id": hid, "harness_arn": hh["arn"], "harness_role": h_role,
           "harness_role_name": "NorthstarHarnessExecutionRole", "gateway_role_name": "NorthstarGatewayServiceRole"})
json.dump(st, open(EV / "state.json", "w"), indent=1)
json.dump({"harness_baseline_policy": HARNESS_BASELINE, "gateway_baseline_policy": GW_BASELINE},
          open(EV / "04_iam_BEFORE.json", "w"), indent=1)
print("OK", hh["arn"], hh["status"])
