import os
import warnings

# When Swagger performs OAuth2 in the browser, it will set
# the request host + relative path as the redirect uri, causing a
# uri mismatch if the oauth_redirect_uri is just the relative path
# is set in the c.JupyterHub.services entry (as per default).
# Therefore need to know the request host ahead of time.
if "PUBLIC_HOST" not in os.environ:
    msg = (
        "env PUBLIC_HOST is not set, defaulting to http://127.0.0.1:8000.  "
        "This can cause problems with OAuth.  "
        "Set PUBLIC_HOST to your public (browser accessible) host."
    )
    warnings.warn(msg)
    public_host = "http://127.0.0.1:8000"
else:
    public_host = os.environ["PUBLIC_HOST"].rstrip('/')
service_name = "fastapi"
oauth_redirect_uri = f"{public_host}/services/{service_name}/oauth_callback"


c = get_config()  # noqa
c.JupyterHub.services = [
    {
        "name": service_name,
        "url": "http://127.0.0.1:10202",
        "command": ["uvicorn", "app:app", "--port", "10202"],
        "oauth_redirect_uri": oauth_redirect_uri,
        "environment": {"PUBLIC_HOST": public_host},
    }
]

c.JupyterHub.load_roles = [
    {
        "name": "service-with-admin-users",
        "services": ["fastapi"],          # Nombre del servicio
        "scopes": ["servers", "admin:users"],        # Permisos para gestionar usuarios
    },
    {
        "name": "user",
        # grant all users access to services
        "scopes": ["servers", "self", "access:services"],
    },
    {
    "name": "admin-role-for-testuser",
    "users": ["test-user"],       # El usuario que quieres que pueda crear
    "scopes": ["servers", "admin:users"],
    },
]


# dummy for testing, create test-user
c.Authenticator.allowed_users = {"test-user"}
c.JupyterHub.authenticator_class = "dummy"
c.JupyterHub.spawner_class = "dockerspawner.DockerSpawner"

# Spawn containers from this image
c.DockerSpawner.image = os.environ["DOCKER_NOTEBOOK_IMAGE"]

# Connect containers to this Docker network
network_name = os.environ["DOCKER_NETWORK_NAME"]
c.DockerSpawner.use_internal_ip = True
c.DockerSpawner.network_name = network_name

# Explicitly set notebook directory because we'll be mounting a volume to it.
# Most `jupyter/docker-stacks` *-notebook images run the Notebook server as
# user `jovyan`, and set the notebook directory to `/home/jovyan/work`.
# We follow the same convention.
notebook_dir = os.environ.get("DOCKER_NOTEBOOK_DIR", "/home/jovyan/work")
c.DockerSpawner.notebook_dir = notebook_dir

# Mount the real user's Docker volume on the host to the notebook user's
# notebook directory in the container
# Monta el volumen persistente por usuario y el compartido para FastAPI
c.DockerSpawner.volumes = {
    "jupyterhub-user-{username}": notebook_dir,
    "fastapi-data": "/data/fastapi"
}


# Remove containers once they are stopped
c.DockerSpawner.remove = False

# For debugging arguments passed to spawned containers
c.DockerSpawner.debug = True

# User containers will access hub by container name on the Docker network
c.JupyterHub.hub_ip = "jupyterhub"
c.JupyterHub.hub_port = 8080

# Persist hub data on volume mounted inside container
c.JupyterHub.cookie_secret_file = "/data/jupyterhub_cookie_secret"
c.JupyterHub.db_url = "sqlite:////data/jupyterhub.sqlite"

# Allow all signed-up users to login
c.Authenticator.allow_all = True

# Authenticate users with Native Authenticator
c.JupyterHub.authenticator_class = "nativeauthenticator.NativeAuthenticator"

# Allow anyone to sign-up without approval
c.NativeAuthenticator.open_signup = True

# Allowed admins
admin = os.environ.get("JUPYTERHUB_ADMIN")
if admin:
    c.Authenticator.admin_users = [admin]