from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
import boto3
import time
from typing import Dict, Tuple

app = FastAPI()

# Configuración ECS
CLUSTER_NAME = "rosblocks-cluster"
TASK_DEFINITION = "rosblocks-task:3"
SUBNETS = ["subnet-09bbc9dcb45a51006"]
SECURITY_GROUPS = ["sg-0d31051e839c56bec"]
REGION = "us-east-1"

# Diccionario en memoria: IP → (taskArn, public_ip)
user_tasks: Dict[str, Tuple[str, str]] = {}

ecs_client = boto3.client("ecs", region_name=REGION)
ec2_client = boto3.client("ec2", region_name=REGION)

def get_public_ip_from_task(task_arn: str) -> str:
    """Obtiene la IP pública asociada a una tarea ECS"""
    try:
        # Obtener detalles de la tarea
        task_desc = ecs_client.describe_tasks(
            cluster=CLUSTER_NAME,
            tasks=[task_arn]
        )
        
        # Obtener ENI ID
        eni_id = task_desc['tasks'][0]['attachments'][0]['details'][1]['value']
        
        # Obtener información de la interfaz de red
        eni_info = ec2_client.describe_network_interfaces(
            NetworkInterfaceIds=[eni_id]
        )
        
        return eni_info['NetworkInterfaces'][0]['Association']['PublicIp']
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error obteniendo IP pública: {str(e)}"
        )

@app.post("/api/get_ip")
async def get_ip(request: Request):
    ip = request.client.host

    if ip in user_tasks:
        task_arn, public_ip = user_tasks[ip]
        return {
            "message": "Ya existe una tarea para esta IP",
            "ip": ip,
            "taskArn": task_arn,
            "publicIp": public_ip
        }

    try:
        # Lanzar nueva tarea
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
        
        # Esperar a que la tarea esté running y obtener su IP
        max_retries = 10
        public_ip = None
        
        for _ in range(max_retries):
            try:
                public_ip = get_public_ip_from_task(task_arn)
                break
            except:
                time.sleep(3)
                continue
        
        if not public_ip:
            raise HTTPException(
                status_code=500,
                detail="No se pudo obtener la IP pública después de varios intentos"
            )

        # Guardar en el diccionario
        user_tasks[ip] = (task_arn, public_ip)

        return {
            "message": "Tarea lanzada",
            "ip": ip,
            "taskArn": task_arn,
            "publicIp": public_ip
        }

    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error lanzando tarea: {str(e)}"
        )

@app.post("/api/stop")
async def stop_task(request: Request):
    ip = request.client.host

    if ip not in user_tasks:
        raise HTTPException(
            status_code=404,
            detail="No hay tarea asociada a esta IP"
        )

    task_arn, public_ip = user_tasks[ip]
    
    try:
        # Detener la tarea
        ecs_client.stop_task(
            cluster=CLUSTER_NAME,
            task=task_arn,
            reason="Petición del usuario"
        )
        
        # Eliminar del diccionario
        del user_tasks[ip]
        
        return {
            "message": "Tarea detenida",
            "ip": ip,
            "publicIp": public_ip,
            "taskArn": task_arn
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error deteniendo tarea: {str(e)}"
        )

@app.get("/api/status")
async def get_status(request: Request):
    ip = request.client.host
    
    if ip not in user_tasks:
        raise HTTPException(
            status_code=404,
            detail="No hay tarea asociada a esta IP"
        )
    
    task_arn, public_ip = user_tasks[ip]
    
    try:
        task_status = ecs_client.describe_tasks(
            cluster=CLUSTER_NAME,
            tasks=[task_arn]
        )['tasks'][0]['lastStatus']
        
        return {
            "ip": ip,
            "publicIp": public_ip,
            "taskArn": task_arn,
            "status": task_status
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error obteniendo estado: {str(e)}"
        )