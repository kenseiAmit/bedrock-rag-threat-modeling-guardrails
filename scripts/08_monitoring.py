"""Task 6: invocation logging -> CloudWatch, metric filter + alarm for guardrail interventions."""
import boto3, json, time, pathlib
EV = pathlib.Path(__file__).parent.parent / "evidence"
st = json.load(open(EV / "state.json")); acct = "269629487409"; region = "us-east-1"
iam = boto3.client("iam"); logs = boto3.client("logs", region_name=region)
br = boto3.client("bedrock", region_name=region); cw = boto3.client("cloudwatch", region_name=region)
LG = "/northstar-assist/bedrock-invocations"; RN = "NorthstarBedrockLoggingRole"
logs.create_log_group(logGroupName=LG)
logs.put_retention_policy(logGroupName=LG, retentionInDays=30)
iam.create_role(RoleName=RN, Description="Bedrock model invocation logging -> CloudWatch (Northstar)",
  AssumeRolePolicyDocument=json.dumps({"Version":"2012-10-17","Statement":[{"Effect":"Allow",
   "Principal":{"Service":"bedrock.amazonaws.com"},"Action":"sts:AssumeRole",
   "Condition":{"StringEquals":{"aws:SourceAccount":acct},"ArnLike":{"aws:SourceArn":f"arn:aws:bedrock:{region}:{acct}:*"}}}]}))
iam.put_role_policy(RoleName=RN, PolicyName="WriteInvocationLogs", PolicyDocument=json.dumps({"Version":"2012-10-17","Statement":[
  {"Effect":"Allow","Action":["logs:CreateLogStream","logs:PutLogEvents"],"Resource":f"arn:aws:logs:{region}:{acct}:log-group:{LG}:log-stream:*"}]}))
time.sleep(10)
br.put_model_invocation_logging_configuration(loggingConfig={
  "cloudWatchConfig":{"logGroupName":LG,"roleArn":f"arn:aws:iam::{acct}:role/{RN}"},
  "textDataDeliveryEnabled":True,"imageDataDeliveryEnabled":False,"embeddingDataDeliveryEnabled":False})
json.dump(br.get_model_invocation_logging_configuration(), open(EV/"09_invocation_logging_config.json","w"), indent=1, default=str)
# metric filter: guardrail interventions recorded in invocation log (stopReason or action)
logs.put_metric_filter(logGroupName=LG, filterName="NorthstarGuardrailIntervened",
  filterPattern='"guardrail_intervened"',
  metricTransformations=[{"metricName":"GuardrailIntervened","metricNamespace":"NorthstarAssist","metricValue":"1","defaultValue":0}])
cw.put_metric_alarm(AlarmName="NorthstarAssist-GuardrailInterventions-High", Namespace="NorthstarAssist",
  MetricName="GuardrailIntervened", Statistic="Sum", Period=3600, EvaluationPeriods=1, Threshold=5,
  ComparisonOperator="GreaterThanThreshold", TreatMissingData="notBreaching",
  AlarmDescription="More than 5 guardrail interventions in 1 hour - possible prompt-injection campaign. See IR playbook.")
st.update(log_group=LG, logging_role=RN); json.dump(st, open(EV/"state.json","w"), indent=1)
print("ok")
