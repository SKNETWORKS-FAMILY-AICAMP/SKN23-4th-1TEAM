import os
import boto3
from dotenv import load_dotenv

load_dotenv(".env", override=True)

AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID", "").strip() or None
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY", "").strip() or None
AWS_REGION = os.getenv("AWS_REGION") or os.getenv("AWS_DEFAULT_REGION") or "ap-northeast-2"
EC2_INSTANCE_ID = os.getenv("EC2_INSTANCE_ID", "").strip() or None

print("ID:", repr(EC2_INSTANCE_ID))
print("Region:", repr(AWS_REGION))

try:
    ec2 = boto3.client(
        "ec2",
        aws_access_key_id=AWS_ACCESS_KEY_ID,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
        region_name=AWS_REGION,
    )
    response = ec2.describe_instances(InstanceIds=[EC2_INSTANCE_ID])
    print("Success!", response)
except Exception as e:
    print("Error:", e)
