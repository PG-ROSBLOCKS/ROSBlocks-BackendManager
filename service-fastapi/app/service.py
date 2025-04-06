import os

from fastapi import APIRouter, Depends, Form, Request, HTTPException
import json
from .client import get_client
from .models import AuthorizationError, HubApiError, User
from .security import get_current_user
import asyncio
import logging
from starlette.concurrency import run_in_threadpool
import docker

# APIRouter prefix cannot end in /
service_prefix = os.getenv("JUPYTERHUB_SERVICE_PREFIX", "").rstrip("/")
router = APIRouter(prefix=service_prefix)


@router.post("/get_token", include_in_schema=False)
async def get_token(code: str = Form(...)):
    "Callback function for OAuth2AuthorizationCodeBearer scheme"
    # The only thing we need in this form post is the code
    # Everything else we can hardcode / pull from env
    async with get_client() as client:
        redirect_uri = (
            os.environ["PUBLIC_HOST"] + os.environ["JUPYTERHUB_OAUTH_CALLBACK_URL"],
        )
        data = {
            "client_id": os.environ["JUPYTERHUB_CLIENT_ID"],
            "client_secret": os.environ["JUPYTERHUB_API_TOKEN"],
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": redirect_uri,
        }
        resp = await client.post("/oauth2/token", data=data)
    ### resp.json() is {'access_token': <token>, 'token_type': 'Bearer'}
    return resp.json()


@router.get("/")
async def index():
    "Non-authenticated function that returns {'Hello': 'World'}"
    return {"Hello": "World"}


# response_model and responses dict translate to OpenAPI (Swagger) hints
# compare and contrast what the /me endpoint looks like in Swagger vs /debug
@router.get(
    "/me",
    response_model=User,
    responses={401: {'model': AuthorizationError}, 400: {'model': HubApiError}},
)
async def me(user: User = Depends(get_current_user)):
    "Authenticated function that returns the User model"
    return user


@router.get("/debug")
async def debug(request: Request, user: User = Depends(get_current_user)):
    """
    Authenticated function that returns a few pieces of debug
     * Environ of the service process
     * Request headers
     * User model
    """
    return {
        "env": dict(os.environ),
        "headers": dict(request.headers),
        "user": user,
    }

#create a new user
@router.post("/create_user")
async def create_user(
    username: str = Form(...),
    user: User = Depends(get_current_user),  # Requiere autenticación para usar este endpoint
):
    """
    Crea un usuario básico en JupyterHub usando la API REST.
    Este endpoint llama a POST /hub/api/users/{username} con un JSON vacío.
    """
    async with get_client() as client:
        # Construir la URL para crear el usuario:
        # Se asume que get_client() ya tiene configurado el base URL con /hub/api
        url = f"/users/{username}"
        # Enviar un POST con cuerpo vacío ({}), ya que la API solo necesita el nombre en la URL
        resp = await client.post(url, json={})
        if resp.status_code == 201:
            return {"msg": "User created successfully"}
        else:
            # Lanza una excepción con detalles en caso de error
            raise HubApiError(detail=resp.json())

#get all users
@router.get("/users")
async def get_users(
    user: User = Depends(get_current_user),  # Requiere autenticación para usar este endpoint
):
    """
    Obtiene una lista de todos los usuarios en JupyterHub usando la API REST.
    Este endpoint llama a GET /hub/api/users.
    """
    async with get_client() as client:
        # Llama a la API para obtener todos los usuarios
        resp = await client.get("/users")
        if resp.status_code == 200:
            return resp.json()
        else:
            # Lanza una excepción con detalles en caso de error
            raise HubApiError(detail=resp.json())
        
def event_stream(session, url):
    """Generator yielding events from a JSON event stream

    For use with the server progress API
    """
    r = session.get(url, stream=True)
    r.raise_for_status()
    for line in r.iter_lines():
        line = line.decode('utf8', 'replace')
        # event lines all start with `data:`
        # all other lines should be ignored (they will be empty)
        if line.startswith('data:'):
            yield json.loads(line.split(':', 1)[1])

#Start a user's single-user notebook server
@router.post("/start_server")
async def start_server(
    username: str = Form(...),
    user: User = Depends(get_current_user),  # Requiere autenticación para usar este endpoint
):
    """
    Inicia el servidor de un usuario específico en JupyterHub usando la API REST.
    Este endpoint llama a POST /hub/api/users/{username}/server
    """
    async with get_client() as client:
        # Construir la URL para iniciar el servidor del usuario
        url = f"/users/{username}/server"
        # Enviar un POST para iniciar el servidor
        resp = await client.post(url)
        if resp.status_code == 201:
            # Si el servidor se inicia correctamente, devuelve la respuesta
            return resp.json()
        else:
            # Lanza una excepción con detalles en caso de error
            raise HubApiError(detail=resp.json())

#Stop a user's single-user notebook server
@router.post("/stop_server")
async def stop_server(
    username: str = Form(...),
    user: User = Depends(get_current_user),  # Requiere autenticación para usar este endpoint
):
    """
    Detiene el servidor de un usuario específico en JupyterHub usando la API REST.
    Este endpoint llama a DELETE /hub/api/users/{username}/server
    """
    async with get_client() as client:
        # Construir la URL para detener el servidor del usuario
        url = f"/users/{username}/server"
        # Enviar un DELETE para detener el servidor
        resp = await client.delete(url)
        if resp.status_code == 204:
            return {"msg": "Server stopped successfully"}
        else:
            # Lanza una excepción con detalles en caso de error
            raise HubApiError(detail=resp.json())

def exec_in_container(container_name: str, command: str):
    """
    Ejecuta un comando en el contenedor especificado y retorna la salida.
    """
    client = docker.from_env()
    try:
        container = client.containers.get(container_name)
    except docker.errors.NotFound:
        log.error(f"Contenedor {container_name} no encontrado")
        raise

    # Ejecuta el comando en el contenedor.
    # 'exec_run' retorna un objeto con .exit_code y .output.
    result = container.exec_run(cmd=command, demux=True)
    stdout, stderr = result.output
    return stdout.decode() if stdout else "", stderr.decode() if stderr else ""

def create_folder_in_container(container_name: str, folder_path: str):
    """
    Crea una carpeta en el contenedor especificado.
    """
    command = f"mkdir -p {folder_path}"
    stdout, stderr = exec_in_container(container_name, command)
    if stderr:
        raise Exception(f"Error creando carpeta: {stderr}")
    return stdout

def create_file_in_container(container_name: str, file_path: str, content: str):
    """
    Crea un archivo en el contenedor especificado.
    """
    command = f"echo '{content}' > {file_path}"
    stdout, stderr = exec_in_container(container_name, command)
    if stderr:
        raise Exception(f"Error creando archivo: {stderr}")
    return stdout


#exec example command on a user's single-user server
@router.post("/exec_in_container")
async def exec_in_container_endpoint(
    username: str = Form(...),
    command: str = Form(...),
    user: User = Depends(get_current_user)
):
    """
    Ejecuta un comando en el contenedor del usuario.
    Se asume que el contenedor se nombra de forma predecible, por ejemplo: 'jupyter-{username}'.
    """
    container_name = f"jupyter-{username}"
    try:
        stdout, stderr = await run_in_threadpool(exec_in_container, container_name, command)
        return {"stdout": stdout, "stderr": stderr}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))