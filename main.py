from fastapi import FastAPI
from kubernetes import client, config
import uuid, time

app = FastAPI()

# Cargar configuración de Kubernetes
config.load_incluster_config()  # Usar load_kube_config() si es local
v1 = client.CoreV1Api()

# Diccionario para manejar sesiones activas (simulación de base de datos)
sessions = {}  # { session_id: {"pod_name": "", "timestamp": 0} }
SESSION_TIMEOUT = 1800  # 30 minutos en segundos

def create_pod(session_id: str):
    """Crea un nuevo pod en Kubernetes para un usuario específico"""
    pod_name = f"rosblocks-{session_id}"

    pod_manifest = {
        "apiVersion": "v1",
        "kind": "Pod",
        "metadata": {"name": pod_name},
        "spec": {
            "containers": [{
                "name": "rosblocks-runtime",
                "image": "juanandresc/rosblocks:latest",  # Imagen de ROSBlocks
                "ports": [{"containerPort": 8000}]
            }]
        }
    }

    v1.create_namespaced_pod(namespace="default", body=pod_manifest)
    sessions[session_id] = {"pod_name": pod_name, "timestamp": time.time()}
    return pod_name

def delete_pod(session_id: str):
    """Elimina el pod de un usuario si ha estado inactivo demasiado tiempo"""
    if session_id in sessions:
        pod_name = sessions[session_id]["pod_name"]
        v1.delete_namespaced_pod(name=pod_name, namespace="default")
        del sessions[session_id]

@app.get("/get-user-pod/{session_id}")
def get_user_pod(session_id: str):
    """Verifica si el usuario ya tiene un pod o le asigna uno nuevo"""
    current_time = time.time()

    if session_id in sessions:
        if current_time - sessions[session_id]["timestamp"] < SESSION_TIMEOUT:
            pod_name = sessions[session_id]["pod_name"]
            pods = v1.list_namespaced_pod(namespace="default", field_selector=f"metadata.name={pod_name}")
            if pods.items:
                pod_ip = pods.items[0].status.pod_ip
                return {"pod_url": f"http://{pod_ip}:8000"}
        else:
            delete_pod(session_id)  # Expiró, eliminarlo

    pod_name = create_pod(session_id)
    return {"message": "Pod created", "pod_name": pod_name}

@app.delete("/delete-user-pod/{session_id}")
def remove_user_pod(session_id: str):
    """Elimina el pod de un usuario manualmente"""
    delete_pod(session_id)
    return {"message": "Pod deleted"}
