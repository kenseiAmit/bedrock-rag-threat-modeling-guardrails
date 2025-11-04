"""Per-request model override test. Usage: 09_override_test.py <phase>"""
import sys, json
from invoke import invoke, EV
st = json.load(open(EV/"state.json"))
ov = {"model": {"bedrockModelConfig": {"modelId": "us.amazon.nova-2-lite-v1:0", "apiFormat": "converse_stream",
      "additionalParams": {"guardrailConfig": {"guardrailIdentifier": st["guardrail_id"], "guardrailVersion": st["guardrail_version"], "trace": "enabled"}}}}}
r = invoke("What is Northstar's hybrid work policy? One sentence.", f"10_{sys.argv[1]}_model_override_nova", ov)
print(r["stop_reason"], r["tool_calls"], r.get("exception"), r["answer"][:200])
