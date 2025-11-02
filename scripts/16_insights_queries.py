"""Run the monitoring-plan Logs Insights queries for real and save results."""
import boto3, json, time, datetime
l = boto3.client("logs", region_name="us-east-1"); G = "/northstar-assist/bedrock-invocations"
Q = {
 "q1_guardrail_interventions_by_hour": 'filter output.outputBodyJson.stopReason = "guardrail_intervened" | stats count() as interventions by bin(1h)',
 "q2_blocked_policy_detail": 'filter output.outputBodyJson.stopReason = "guardrail_intervened" | parse @message /"filters":\\[\\{"type":"(?<attack>[A-Z_]+)"/ | stats count() by attack',
 "q3_token_anomaly_top": 'filter output.outputBodyJson.usage.totalTokens > 8000 | fields @timestamp, requestId, output.outputBodyJson.usage.totalTokens as tokens | sort tokens desc | limit 10',
 "q4_calls_by_identity_model": 'stats count() as calls, sum(output.outputBodyJson.usage.totalTokens) as tokens by identity.arn, modelId',
 "q5_zero_chunk_retrieval": 'filter @message like /\\"retrievalResults\\\\\\":\\[\\]/ | stats count() as zero_chunk_results',
}
out = {}
end = int(time.time()); start = end - 6 * 3600
for k, q in Q.items():
    qid = l.start_query(logGroupName=G, startTime=start, endTime=end, queryString=q)["queryId"]
    while True:
        r = l.get_query_results(queryId=qid)
        if r["status"] in ("Complete", "Failed", "Cancelled"): break
        time.sleep(2)
    out[k] = {"query": q, "status": r["status"], "rows": [{c["field"]: c["value"] for c in row} for row in r["results"]]}
    print(k, r["status"], out[k]["rows"][:6])
json.dump(out, open("evidence/19_insights_queries.json", "w"), indent=1)
