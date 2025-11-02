"""Task 4: replace broad baseline policies with least-privilege ones; save AFTER state."""
import boto3, json, pathlib
EV = pathlib.Path(__file__).parent.parent / "evidence"
st = json.load(open(EV/"state.json")); A = "269629487409"; R = "us-east-1"
iam = boto3.client("iam")
M = "anthropic.claude-sonnet-4-5-20250929-v1:0"
GARN = st["guardrail_arn"]
HP = {"Version":"2012-10-17","Statement":[
 {"Sid":"InvokeApprovedModelOnly","Effect":"Allow","Action":["bedrock:InvokeModel","bedrock:InvokeModelWithResponseStream"],
  "Resource":[f"arn:aws:bedrock:{R}:{A}:inference-profile/us.{M}",
              f"arn:aws:bedrock:us-east-1::foundation-model/{M}",f"arn:aws:bedrock:us-east-2::foundation-model/{M}",f"arn:aws:bedrock:us-west-2::foundation-model/{M}"]},
 {"Sid":"RequireNorthstarGuardrail","Effect":"Deny","Action":["bedrock:InvokeModel","bedrock:InvokeModelWithResponseStream"],"Resource":"*",
  "Condition":{"ArnNotLike":{"bedrock:GuardrailIdentifier":[GARN,GARN+":*"]}}},
 {"Sid":"InvokeNorthstarGateway","Effect":"Allow","Action":"bedrock-agentcore:InvokeGateway","Resource":st["gateway_arn"]},
 {"Sid":"RuntimeLogs","Effect":"Allow","Action":["logs:CreateLogGroup","logs:DescribeLogStreams","logs:CreateLogStream","logs:PutLogEvents"],
  "Resource":[f"arn:aws:logs:{R}:{A}:log-group:/aws/bedrock-agentcore/runtimes/harness_NorthstarAssist-88mkHp4jsF-*",
              f"arn:aws:logs:{R}:{A}:log-group:/aws/bedrock-agentcore/runtimes/harness_NorthstarAssist-88mkHp4jsF-*:log-stream:*"]},
 {"Sid":"RuntimeImageAndTelemetry","Effect":"Allow","Action":["ecr-public:GetAuthorizationToken","sts:GetServiceBearerToken","xray:PutTraceSegments","xray:PutTelemetryRecords"],"Resource":"*"},
 {"Sid":"RuntimeManagedImage","Effect":"Allow","Action":"ecr:GetAuthorizationToken","Resource":"*"},
 {"Sid":"RuntimeManagedImagePull","Effect":"Allow","Action":["ecr:BatchGetImage","ecr:GetDownloadUrlForLayer","ecr:BatchCheckLayerAvailability"],"Resource":f"arn:aws:ecr:{R}:*:repository/harness-*"},
 {"Sid":"WorkloadIdentity","Effect":"Allow","Action":["bedrock-agentcore:GetWorkloadAccessToken","bedrock-agentcore:GetWorkloadAccessTokenForJWT"],
  "Resource":[f"arn:aws:bedrock-agentcore:{R}:{A}:workload-identity-directory/default",
              f"arn:aws:bedrock-agentcore:{R}:{A}:workload-identity-directory/default/workload-identity/harness_NorthstarAssist-*"]}]}
GP = {"Version":"2012-10-17","Statement":[
 {"Sid":"ReadOwnGateway","Effect":"Allow","Action":"bedrock-agentcore:GetGateway","Resource":st["gateway_arn"]},
 {"Sid":"ReadConfigBundle","Effect":"Allow","Action":"bedrock-agentcore:GetConfigurationBundleVersion","Resource":f"arn:aws:bedrock-agentcore:{R}:{A}:configuration-bundle/*"},
 {"Sid":"RetrieveFromNorthstarKbOnly","Effect":"Allow","Action":["bedrock:GetKnowledgeBase","bedrock:Retrieve"],"Resource":f"arn:aws:bedrock:{R}:{A}:knowledge-base/{st['kb_id']}"}]}
iam.put_role_policy(RoleName=st["harness_role_name"], PolicyName="HarnessScopedPolicy", PolicyDocument=json.dumps(HP))
try: iam.delete_role_policy(RoleName=st["harness_role_name"], PolicyName="HarnessBaselinePolicy")
except iam.exceptions.NoSuchEntityException: pass
iam.put_role_policy(RoleName=st["gateway_role_name"], PolicyName="GatewayScopedPolicy", PolicyDocument=json.dumps(GP))
try: iam.delete_role_policy(RoleName=st["gateway_role_name"], PolicyName="GatewayBaselinePolicy")
except iam.exceptions.NoSuchEntityException: pass
after = {}
for rn in (st["harness_role_name"], st["gateway_role_name"]):
    after[rn] = {p: iam.get_role_policy(RoleName=rn, PolicyName=p)["PolicyDocument"] for p in iam.list_role_policies(RoleName=rn)["PolicyNames"]}
json.dump(after, open(EV/"11_iam_AFTER.json","w"), indent=1)
print({k: list(v) for k, v in after.items()})
