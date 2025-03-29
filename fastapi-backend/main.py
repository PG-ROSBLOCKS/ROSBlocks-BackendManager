from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import boto3
import uuid

app = FastAPI()

# Configuración ECS
CLUSTER_NAME = "rosblocks-cluster"
TASK_DEFINITION = "rosblocks-task:3"
SUBNETS = ["subnet-09bbc9dcb45a51006"]
SECURITY_GROUPS = ["sg-0d31051e839c56bec"]

# Diccionario en memoria: IP → taskArn
user_tasks = {}

ecs_client = boto3.client("ecs", region_name="us-east-1")  # Ajusta región si no es us-east-1

@app.post("/api/get_ip")
async def get_ip(request: Request):
    ip = request.client.host

    if ip in user_tasks:
        return {"message": "Ya existe una tarea para esta IP", "ip": ip, "taskArn": user_tasks[ip]}

    try:
        response = ecs_client.run_task(
            cluster=CLUSTER_NAME,
            launchType="FARGATE",
            taskDefinition=TASK_DEFINITION,
            count=1,
            platformVersion="LATEST",
            networkConfiguration={
                "awsvpcConfiguration": {
                    "subnets": SUBNETS,
                    "securityGroups": SECURITY_GROUPS,
                    "assignPublicIp": "ENABLED"
                }
            }
        )

        task_arn = response["tasks"][0]["taskArn"]
        user_tasks[ip] = task_arn

        return {"message": "Tarea lanzada", "ip": ip, "taskArn": task_arn}

    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.post("/api/stop")
async def stop_task(request: Request):
    ip = request.client.host

    task_arn = user_tasks.get(ip)
    if not task_arn:
        return JSONResponse(status_code=404, content={"error": "No hay tarea asociada a esta IP"})

    try:
        ecs_client.stop_task(cluster=CLUSTER_NAME, task=task_arn, reason="Petición del usuario")
        del user_tasks[ip]
        return {"message": "Tarea detenida", "ip": ip}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})
