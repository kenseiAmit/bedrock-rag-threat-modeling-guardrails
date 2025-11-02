"""Delete every AWS resource created for Northstar Assist; record outcome."""
import boto3, json, time
R="us-east-1"; s=json.load(open("evidence/state.json")); log=[]
ac=boto3.client("bedrock-agentcore-control",region_name=R); ba=boto3.client("bedrock-agent",region_name=R)
bd=boto3.client("bedrock",region_name=R); s3=boto3.resource("s3",region_name=R)
cw=boto3.client("cloudwatch",region_name=R); lg=boto3.client("logs",region_name=R); iam=boto3.client("iam")
def step(name,fn):
    try: fn(); log.append((name,"ok"))
    except Exception as e: log.append((name,"ERR "+str(e)[:160]))
    print(log[-1])
def wait(fn,exc,n=40):
    for _ in range(n):
        try: fn(); time.sleep(6)
        except Exception as e:
            if exc in str(e) or "NotFound" in str(e) or "ResourceNotFound" in str(e): return
            time.sleep(6)
step("delete harness",lambda: ac.delete_harness(harnessId=s["harness_id"]))
wait(lambda: ac.get_harness(harnessId=s["harness_id"]),"NotFound")
step("delete gateway target",lambda: ac.delete_gateway_target(gatewayIdentifier=s["gateway_id"],targetId=s["target_id"]))
wait(lambda: ac.get_gateway_target(gatewayIdentifier=s["gateway_id"],targetId=s["target_id"]),"NotFound")
step("delete gateway",lambda: ac.delete_gateway(gatewayIdentifier=s["gateway_id"]))
step("delete data source",lambda: ba.delete_data_source(knowledgeBaseId=s["kb_id"],dataSourceId=s["ds_id"]))
time.sleep(15)
step("delete KB",lambda: ba.delete_knowledge_base(knowledgeBaseId=s["kb_id"]))
step("delete guardrail",lambda: bd.delete_guardrail(guardrailIdentifier=s["guardrail_id"]))
def empty():
    b=s3.Bucket(s["bucket"]); b.object_versions.delete(); b.delete()
step("empty+delete bucket",empty)
step("delete alarm",lambda: cw.delete_alarms(AlarmNames=["NorthstarAssist-GuardrailInterventions-High"]))
step("delete metric filter",lambda: lg.delete_metric_filter(logGroupName=s["log_group"],filterName="NorthstarGuardrailIntervened"))
step("disable invocation logging",lambda: bd.delete_model_invocation_logging_configuration())
step("delete log group",lambda: lg.delete_log_group(logGroupName=s["log_group"]))
for g in lg.describe_log_groups(logGroupNamePrefix="/aws/bedrock-agentcore/runtimes/harness_NorthstarAssist")["logGroups"]:
    step("delete log group "+g["logGroupName"],lambda g=g: lg.delete_log_group(logGroupName=g["logGroupName"]))
for r in ["NorthstarHarnessExecutionRole","NorthstarGatewayServiceRole","NorthstarAssistKBServiceRole","NorthstarBedrockLoggingRole"]:
    def d(r=r):
        for p in iam.list_role_policies(RoleName=r)["PolicyNames"]: iam.delete_role_policy(RoleName=r,PolicyName=p)
        for p in iam.list_attached_role_policies(RoleName=r)["AttachedPolicies"]: iam.detach_role_policy(RoleName=r,PolicyArn=p["PolicyArn"])
        iam.delete_role(RoleName=r)
    step("delete role "+r,d)
json.dump(log,open("evidence/99_teardown.json","w"),indent=1)
