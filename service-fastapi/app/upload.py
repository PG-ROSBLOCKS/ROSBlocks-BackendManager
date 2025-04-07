# app/routers/upload.py

from fastapi import APIRouter, HTTPException, Depends, Form
# from .models import UploadRequest
from .security import get_current_user  # si manejas auth, ejemplo

router = APIRouter()

@router.post("/", response_model=dict)
async def upload_code(
    username: str = Form(...),
    # request: UploadRequest = Depends(),
    # user: User = Depends(get_current_user)  # si requieres auth
):
    """
 

# Funciones auxiliares

# async def generate_pub_sub(username: str, req: UploadRequest) -> dict:
#     # TODO: subir el código al pod jupyter-{username}:8000 
#     # o usar la API K8s / exec_in_container
#     return {"status": "OK", "msg": "pub_sub generated"}

# async def generate_service(username: str, req: UploadRequest) -> dict:
#     # ...
#     return {"status": "OK", "msg": "service generated"}

# async def generate_message(username: str, req: UploadRequest) -> dict:
#     # ...
#     return {"status": "OK", "msg": "message generated"}

# async def generate_server(username: str, req: UploadRequest) -> dict:
#     # ...
#     return {"status": "OK", "msg": "server generated"}

# async def generate_client(username: str, req: UploadRequest) -> dict:
#     # ...
#     return {"status": "OK", "msg": "client generated"}
