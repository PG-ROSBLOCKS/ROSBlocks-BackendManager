from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Dict
import boto3
import time
from fastapi.middleware.cors import CORSMiddleware
import os

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
    "https://rosblocks.com.co",
    "https://www.rosblocks.com.co"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


CLUSTER_NAME = "rosblocks-cluster"
TASK_DEFINITION = "rosblocks-task:4"
SUBNETS = ["subnet-0b11871fcb08f92c6"]
SECURITY_GROUPS = ["sg-0ad9016ead45bf057"]

ecs_client = boto3.client("ecs", region_name="us-east-1")
ec2_client = boto3.client("ec2", region_name="us-east-1")

sessions: Dict[str, str] = {}

# ------------------------------------------

@app.get("/api/get-ip/{uuid}")
def get_ip(uuid: str):
    if uuid in sessions:
        task_arn = sessions[uuid]
        task_info = get_task_status(task_arn)
        if task_info["status"] == "RUNNING":
            regenerate_mapping(sessions)
            return {"status": "ready", "path": f"/session/{uuid}/"}
        else:
            return {"status": "starting"}
    else:
        task_arn = launch_task()
        sessions[uuid] = task_arn
        print(f"Task launched with ARN: {task_arn}")
        return {"status": "starting"}

class DeleteRequest(BaseModel):
    task_arn: str

@app.post("/api/delete-task")
def delete_task(req: DeleteRequest):
    task_arn = req.task_arn
    uuid_to_delete = None
    for uuid, arn in sessions.items():
        if arn == task_arn:
            uuid_to_delete = uuid
            break

    if uuid_to_delete:
        del sessions[uuid_to_delete]
        regenerate_mapping(sessions)
        try:
            ecs_client.stop_task(
                cluster=CLUSTER_NAME,
                task=task_arn,
                reason="Inactivity timeout from container"
            )
            print(f"Task {task_arn} stopped successfully.")
        except Exception as e:
            print(f"Error stopping task {task_arn}: {e}")
        return {"status": "deleted", "uuid": uuid_to_delete}
    else:
        raise HTTPException(status_code=404, detail="Task not found")

def launch_task() -> str:
    response = ecs_client.run_task(
        cluster=CLUSTER_NAME,
        launchType="FARGATE",
        taskDefinition=TASK_DEFINITION,
        networkConfiguration={
            "awsvpcConfiguration": {
                "subnets": SUBNETS,
                "securityGroups": SECURITY_GROUPS,
                "assignPublicIp": "ENABLED"
            }
        }
    )
    return response["tasks"][0]["taskArn"]

def get_task_status(task_arn: str) -> dict:
    desc = ecs_client.describe_tasks(cluster=CLUSTER_NAME, tasks=[task_arn])
    task = desc["tasks"][0]
    last_status = task["lastStatus"]

    if last_status != "RUNNING":
        return {"status": last_status}

    eni_id = next(
        (d["value"] for d in task["attachments"][0]["details"] if d["name"] == "networkInterfaceId"),
        None
    )
    eni_data = ec2_client.describe_network_interfaces(NetworkInterfaceIds=[eni_id])
    ip = eni_data["NetworkInterfaces"][0]["PrivateIpAddress"]
    return {"status": "RUNNING", "ip": ip}

def regenerate_mapping(sessions: Dict[str, str]):
    mapping_file = "/etc/nginx/mappings/user_sessions.map"
    os.makedirs(os.path.dirname(mapping_file), exist_ok=True)

    lines = ["map $uuid $backend_ip {\n", "    default 127.0.0.1;\n"]
    
    for uuid, task_arn in sessions.items():
        task_info = get_task_status(task_arn)
        ip = task_info.get("ip", "127.0.0.1")
        lines.append(f'    "{uuid}" {ip};\n')
    
    lines.append("}\n")

    with open(mapping_file, "w") as f:
        f.writelines(lines)
    print(f"Updated mapping file: {mapping_file}")

    os.system("nginx -s reload")


