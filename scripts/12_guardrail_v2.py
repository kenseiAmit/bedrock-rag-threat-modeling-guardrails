"""Tune guardrail: credentials topic must not block questions about password *policy*. Creates version 2 (v1 kept for the record)."""
import boto3, json, time, pathlib
EV = pathlib.Path(__file__).parent.parent / "evidence"; st = json.load(open(EV/"state.json"))
br = boto3.client("bedrock", region_name="us-east-1")
g = br.get_guardrail(guardrailIdentifier=st["guardrail_id"], guardrailVersion="DRAFT")
topics = g["topicPolicy"]["topics"]
for t in topics:
    if t["name"] == "Credentials and infrastructure secrets":
        t["definition"] = "Requests to reveal actual secret values or infrastructure identifiers such as real passwords, access keys, tokens, account numbers or instance IDs. Policy questions are not included."
        t["examples"] = ["What is the production database password?", "Give me the AWS access key for the deploy user",
                         "List the AWS account IDs and EC2 instance IDs", "What credentials are in the infrastructure inventory?"]
    t.pop("inputAction", None); t.pop("outputAction", None); t.pop("inputEnabled", None); t.pop("outputEnabled", None)
br.update_guardrail(guardrailIdentifier=st["guardrail_id"], name=g["name"], description=g["description"],
    topicPolicyConfig={"topicsConfig": topics},
    contentPolicyConfig={"filtersConfig": [{k: v for k, v in f.items() if k in ("type","inputStrength","outputStrength")} for f in g["contentPolicy"]["filters"]]},
    sensitiveInformationPolicyConfig={"piiEntitiesConfig": [{"type": e["type"], "action": e["action"]} for e in g["sensitiveInformationPolicy"]["piiEntities"]]},
    blockedInputMessaging=g["blockedInputMessaging"], blockedOutputsMessaging=g["blockedOutputsMessaging"])
time.sleep(5)
v = br.create_guardrail_version(guardrailIdentifier=st["guardrail_id"], description="v2 tuned credentials topic (policy questions allowed)")["version"]
json.dump(br.get_guardrail(guardrailIdentifier=st["guardrail_id"], guardrailVersion=v), open(EV/"08_guardrail_v2.json","w"), indent=1, default=str)
print("version", v)
