import boto3
import streamlit as st
from utils.config import (
    AWS_ACCESS_KEY_ID,
    AWS_SECRET_ACCESS_KEY,
    AWS_REGION,
    EC2_INSTANCE_ID,
)


@st.cache_resource
def get_ec2_client():
    """Boto3 EC2 클라이언트 싱글톤 반환"""
    if not AWS_ACCESS_KEY_ID or not AWS_SECRET_ACCESS_KEY:
        raise ValueError("AWS Credentials not found.")

    return boto3.client(
        "ec2",
        aws_access_key_id=AWS_ACCESS_KEY_ID,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
        region_name=AWS_REGION,
    )


def get_instance_info():
    """현재 EC2 인스턴스의 상태 및 IP 정보를 조회"""
    if not EC2_INSTANCE_ID:
        return {"error": "EC2_INSTANCE_ID가 설정되지 않았습니다. .env 파일을 확인해주세요."}
    
    # 앞뒤 보이지 않는 유니코드 공백이나 따옴표 등 모든 특수문자 완벽히 제거
    import re
    clean_id = re.sub(r'[^a-zA-Z0-9-]', '', EC2_INSTANCE_ID)
    
    try:
        ec2 = get_ec2_client()
        response = ec2.describe_instances(InstanceIds=[clean_id])

        if not response.get("Reservations"):
            return {"error": "No reservations found for this Instance ID"}

        instance = response["Reservations"][0]["Instances"][0]
        state = instance["State"]["Name"]
        ip = instance.get("PublicIpAddress", "N/A")
        type_ = instance["InstanceType"]
        launch_time = instance["LaunchTime"]

        return {"state": state, "ip": ip, "type": type_, "launch_time": launch_time}
    except Exception as e:
        return {"error": str(e)}


def _get_clean_id():
    import re
    if not EC2_INSTANCE_ID:
        return None
    return re.sub(r'[^a-zA-Z0-9-]', '', EC2_INSTANCE_ID)

def start_instance():
    """서버(EC2 인스턴스) 시작"""
    clean_id = _get_clean_id()
    if not clean_id:
        raise ValueError("EC2_INSTANCE_ID is missing")
    return get_ec2_client().start_instances(InstanceIds=[clean_id])


def stop_instance():
    """서버(EC2 인스턴스) 중지"""
    clean_id = _get_clean_id()
    if not clean_id:
        raise ValueError("EC2_INSTANCE_ID is missing")
    return get_ec2_client().stop_instances(InstanceIds=[clean_id])
