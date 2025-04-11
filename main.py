from fastapi import FastAPI, Request, HTTPException
from pydantic import BaseModel
from typing import Dict, List

app = FastAPI()

# IPs predefinidas
AVAILABLE_IPS = [
    "3.90.1.1", "3.90.1.2", "3.90.1.3", "3.90.1.4", "3.90.1.5",
    "3.90.1.6", "3.90.1.7", "3.90.1.8", "3.90.1.9", "3.90.1.10"
]

# Estados
ip_pool: List[str] = AVAILABLE_IPS.copy()
client_assignments: Dict[str, str] = {}  # client_id → assigned_ip
reverse_assignments: Dict[str, str] = {}  # assigned_ip → client_id

class ClientRequest(BaseModel):
    client_id: str

class ReleaseRequest(BaseModel):
    ip_to_release: str

@app.post("/api/get_ip")
async def get_ip(data: ClientRequest):
    client_id = data.client_id

    if client_id in client_assignments:
        assigned_ip = client_assignments[client_id]
        return {
            "message": "Ya tienes una IP asignada",
            "clientId": client_id,
            "assignedIp": assigned_ip
        }

    if not ip_pool:
        raise HTTPException(
            status_code=503,
            detail="No hay IPs disponibles en este momento"
        )

    assigned_ip = ip_pool.pop(0)
    client_assignments[client_id] = assigned_ip
    reverse_assignments[assigned_ip] = client_id

    return {
        "message": "IP asignada correctamente",
        "clientId": client_id,
        "assignedIp": assigned_ip
    }

@app.post("/api/stop")
async def stop_task(data: ClientRequest):
    client_id = data.client_id

    if client_id not in client_assignments:
        raise HTTPException(
            status_code=404,
            detail="No tienes ninguna IP asignada"
        )

    assigned_ip = client_assignments[client_id]

    # Liberar
    del client_assignments[client_id]
    del reverse_assignments[assigned_ip]
    ip_pool.append(assigned_ip)

    return {
        "message": "IP liberada correctamente",
        "clientId": client_id,
        "releasedIp": assigned_ip
    }

@app.get("/api/status")
async def get_status(client_id: str):
    if client_id not in client_assignments:
        raise HTTPException(
            status_code=404,
            detail="No tienes ninguna IP asignada"
        )

    assigned_ip = client_assignments[client_id]
    return {
        "clientId": client_id,
        "assignedIp": assigned_ip,
        "status": "asignada"
    }

@app.get("/api/pool_status")
async def pool_status():
    return {
        "total": len(AVAILABLE_IPS),
        "disponibles": len(ip_pool),
        "asignadas": len(client_assignments),
        "detalles": client_assignments
    }

@app.post("/api/release_ip")
async def release_ip(data: ReleaseRequest, request: Request):
    ip_to_release = data.ip_to_release
    requester_ip = request.client.host

    if ip_to_release not in reverse_assignments:
        raise HTTPException(
            status_code=404,
            detail="La IP no está actualmente asignada"
        )

    client_id = reverse_assignments[ip_to_release]

    # Liberar
    del client_assignments[client_id]
    del reverse_assignments[ip_to_release]
    ip_pool.append(ip_to_release)

    return {
        "message": "IP liberada por timeout",
        "releasedIp": ip_to_release,
        "clientId": client_id
    }
