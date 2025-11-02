"""Invoke the Northstar harness and capture the complete raw event stream as evidence."""
import json, sys, time, uuid, pathlib, datetime, boto3

W = pathlib.Path(__file__).resolve().parents[1]
EV = W / "evidence"


def invoke(prompt, label, extra=None):
    st = json.load(open(EV / "state.json"))
    client = boto3.client("bedrock-agentcore", region_name="us-east-1")
    sid = "northstar-" + uuid.uuid4().hex  # >= 33 chars
    t0 = time.time()
    kw = dict(harnessArn=st["harness_arn"], runtimeSessionId=sid,
              messages=[{"role": "user", "content": [{"text": prompt}]}])
    kw.update(extra or {})
    rec = {"label": label, "prompt": prompt, "session_id": sid,
           "timestamp_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(), "events": []}
    answer, stop, tools = "", None, []
    try:
        resp = client.invoke_harness(**kw)
        rec["request_id"] = resp["ResponseMetadata"]["RequestId"]
        for ev in resp["stream"]:
            rec["events"].append(ev)
            if "contentBlockDelta" in ev:
                d = ev["contentBlockDelta"]["delta"]
                if "text" in d:
                    answer += d["text"]
            elif "contentBlockStart" in ev:
                s = ev["contentBlockStart"].get("start", {})
                if "toolUse" in s:
                    tools.append(s["toolUse"].get("name"))
            elif "messageStop" in ev:
                stop = ev["messageStop"]["stopReason"]
    except Exception as e:  # recorded, not hidden
        rec["exception"] = f"{type(e).__name__}: {e}"
    rec.update(answer=answer, stop_reason=stop, tool_calls=tools, seconds=round(time.time() - t0, 2))
    out = EV / f"{label}.json"
    json.dump(rec, open(out, "w"), indent=1, default=str)
    return rec


if __name__ == "__main__":
    r = invoke(sys.argv[2], sys.argv[1])
    print("TOOLS:", r["tool_calls"], "STOP:", r["stop_reason"], "EXC:", r.get("exception"))
    print("ANSWER:\n", r["answer"])
