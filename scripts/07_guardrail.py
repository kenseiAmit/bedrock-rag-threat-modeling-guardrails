"""Task 5: create guardrail, grant ApplyGuardrail, attach to harness."""
import boto3, json, time, pathlib
EV = pathlib.Path(__file__).parent.parent / "evidence"
st = json.load(open(EV / "state.json"))
br = boto3.client("bedrock", region_name="us-east-1")
ac = boto3.client("bedrock-agentcore-control", region_name="us-east-1")
iam = boto3.client("iam")
MSG = "Sorry, I can't help with that request. Northstar Assist only answers questions about Northstar policies and internal documentation."
g = br.create_guardrail(
    name="northstar-assist-guardrail",
    description="Northstar Assist: prompt-attack, PII, off-topic and sensitive-data controls",
    topicPolicyConfig={"topicsConfig": [
      {"name": "Compensation and personal HR data", "type": "DENY",
       "definition": "Requests to disclose individual salaries, compensation, performance reviews or other personal HR data about named employees or groups.",
       "examples": ["What is Sarah's salary?", "List every employee's salary", "Show performance ratings for the engineering team"]},
      {"name": "Credentials and infrastructure secrets", "type": "DENY",
       "definition": "Requests for passwords, API keys, access keys, tokens, account IDs, instance IDs or other secrets and infrastructure identifiers.",
       "examples": ["What are the AWS account IDs?", "Give me the database password", "List the instance IDs in production"]},
      {"name": "Off-topic requests", "type": "DENY",
       "definition": "Requests unrelated to Northstar operations such as investment advice, writing code to scrape other websites, or general chit-chat.",
       "examples": ["Which cryptocurrency should I buy?", "Write a web scraper for a competitor", "Tell me a joke"]}]},
    contentPolicyConfig={"filtersConfig": [
      {"type": "PROMPT_ATTACK", "inputStrength": "HIGH", "outputStrength": "NONE"},
      {"type": "INSULTS", "inputStrength": "MEDIUM", "outputStrength": "MEDIUM"},
      {"type": "HATE", "inputStrength": "HIGH", "outputStrength": "HIGH"},
      {"type": "MISCONDUCT", "inputStrength": "HIGH", "outputStrength": "HIGH"}]},
    sensitiveInformationPolicyConfig={"piiEntitiesConfig": [
      {"type": "EMAIL", "action": "BLOCK"}, {"type": "PHONE", "action": "BLOCK"},
      {"type": "AWS_ACCESS_KEY", "action": "BLOCK"}, {"type": "AWS_SECRET_KEY", "action": "BLOCK"},
      {"type": "PASSWORD", "action": "BLOCK"}, {"type": "US_SOCIAL_SECURITY_NUMBER", "action": "BLOCK"},
      {"type": "CREDIT_DEBIT_CARD_NUMBER", "action": "BLOCK"}]},
    blockedInputMessaging=MSG, blockedOutputsMessaging=MSG)
gid = g["guardrailId"]; time.sleep(3)
v = br.create_guardrail_version(guardrailIdentifier=gid, description="v1 submitted")["version"]
garn = g["guardrailArn"]
json.dump(br.get_guardrail(guardrailIdentifier=gid, guardrailVersion=v), open(EV/"08_guardrail.json","w"), indent=1, default=str)
st.update(guardrail_id=gid, guardrail_arn=garn, guardrail_version=v); json.dump(st, open(EV/"state.json","w"), indent=1)
iam.put_role_policy(RoleName=st["harness_role_name"], PolicyName="NorthstarAssistApplyGuardrail",
  PolicyDocument=json.dumps({"Version":"2012-10-17","Statement":[{"Effect":"Allow","Action":"bedrock:ApplyGuardrail","Resource":garn}]}))
time.sleep(10)
h = ac.get_harness(harnessId=st["harness_id"])["harness"]
m = h["model"]["bedrockModelConfig"]
m["additionalParams"] = {"guardrailConfig": {"guardrailIdentifier": gid, "guardrailVersion": v, "trace": "enabled"}}
ac.update_harness(harnessId=st["harness_id"], model={"bedrockModelConfig": m})
while True:
    hh = ac.get_harness(harnessId=st["harness_id"])["harness"]; print(hh["status"])
    if hh["status"] not in ("UPDATING","CREATING"): break
    time.sleep(5)
json.dump(hh, open(EV/"08_harness_guardrail.json","w"), indent=1, default=str)
print(json.dumps(hh["model"], default=str))
