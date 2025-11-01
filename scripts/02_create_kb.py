"""Task 1a: create the Managed Knowledge Base, S3 data source, and run a sync."""
import json, time, pathlib, boto3

W = pathlib.Path(__file__).resolve().parents[1]
EV = W / "evidence"
suffix = (EV / "suffix.txt").read_text().strip()
bucket = f"northstar-assist-kb-{suffix}"
region = "us-east-1"
acct = boto3.client("sts").get_caller_identity()["Account"]
iam = boto3.client("iam")
ba = boto3.client("bedrock-agent", region_name=region)

role_name = "NorthstarAssistKBServiceRole"
trust = {"Version": "2012-10-17", "Statement": [{
    "Effect": "Allow", "Principal": {"Service": "bedrock.amazonaws.com"}, "Action": "sts:AssumeRole",
    "Condition": {"StringEquals": {"aws:SourceAccount": acct}}}]}
policy = {"Version": "2012-10-17", "Statement": [
    {"Sid": "ReadDocBucket", "Effect": "Allow", "Action": ["s3:GetObject", "s3:ListBucket"],
     "Resource": [f"arn:aws:s3:::{bucket}", f"arn:aws:s3:::{bucket}/*"],
     "Condition": {"StringEquals": {"aws:ResourceAccount": acct}}},
    {"Sid": "InvokeTitanEmbed", "Effect": "Allow", "Action": "bedrock:InvokeModel",
     "Resource": f"arn:aws:bedrock:{region}::foundation-model/amazon.titan-embed-text-v2:0"}]}
try:
    role = iam.create_role(RoleName=role_name, AssumeRolePolicyDocument=json.dumps(trust),
                           Description="Northstar Assist KB service role")["Role"]
except iam.exceptions.EntityAlreadyExistsException:
    role = iam.get_role(RoleName=role_name)["Role"]
iam.put_role_policy(RoleName=role_name, PolicyName="NorthstarKBAccess", PolicyDocument=json.dumps(policy))
time.sleep(12)

existing = [k for k in ba.list_knowledge_bases()["knowledgeBaseSummaries"] if k["name"] == "northstar-assist-kb"]
kb = {"knowledgeBaseId": existing[0]["knowledgeBaseId"], "status": "EXISTING"} if existing else ba.create_knowledge_base(
    name="northstar-assist-kb",
    description="Northstar Assist managed knowledge base",
    roleArn=role["Arn"],
    knowledgeBaseConfiguration={
        "type": "MANAGED",
        "managedKnowledgeBaseConfiguration": {
            "embeddingModelType": "CUSTOM",
            "embeddingModelArn": f"arn:aws:bedrock:{region}::foundation-model/amazon.titan-embed-text-v2:0"}},
)["knowledgeBase"]
kb_id = kb["knowledgeBaseId"]
print("KB", kb_id, kb["status"])
while True:
    st = ba.get_knowledge_base(knowledgeBaseId=kb_id)["knowledgeBase"]
    print(" status", st["status"])
    if st["status"] not in ("CREATING",):
        break
    time.sleep(10)
json.dump(st, open(EV / "02_kb.json", "w"), indent=1, default=str)

ds = ba.create_data_source(
    knowledgeBaseId=kb_id, name="northstar-documents",
    dataSourceConfiguration={"type": "MANAGED_KNOWLEDGE_BASE_CONNECTOR",
        "managedKnowledgeBaseConnectorConfiguration": {"connectorParameters": {
            "type": "S3", "version": "1",
            "connectionConfiguration": {"bucketName": bucket, "bucketOwnerAccountId": acct}}}},
)["dataSource"]
ds_id = ds["dataSourceId"]
while ba.get_data_source(knowledgeBaseId=kb_id, dataSourceId=ds_id)["dataSource"]["status"] == "CREATING":
    time.sleep(5)
job = ba.start_ingestion_job(knowledgeBaseId=kb_id, dataSourceId=ds_id)["ingestionJob"]
while True:
    j = ba.get_ingestion_job(knowledgeBaseId=kb_id, dataSourceId=ds_id, ingestionJobId=job["ingestionJobId"])["ingestionJob"]
    print(" sync", j["status"], j.get("statistics"))
    if j["status"] in ("COMPLETE", "FAILED", "STOPPED"):
        break
    time.sleep(15)
json.dump(j, open(EV / "02_ingestion_job.json", "w"), indent=1, default=str)
json.dump({"kb_id": kb_id, "ds_id": ds_id, "kb_role_arn": role["Arn"], "bucket": bucket},
          open(EV / "state.json", "w"), indent=1)
