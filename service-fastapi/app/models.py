from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel


# https://jupyterhub.readthedocs.io/en/stable/_static/rest-api/index.html
class Server(BaseModel):
    name: str
    ready: bool
    pending: Optional[str]
    url: str
    progress_url: str
    started: datetime
    last_activity: datetime
    state: Optional[Any]
    user_options: Optional[Any]


class User(BaseModel):
    kind: Optional[str] = None
    name: str
    admin: bool
    scopes: List[str]
    server: Optional[str] = None
    pending: Optional[str] = None
    last_activity: Optional[datetime] = None
    servers: Optional[Dict[str, Server]] = None


# https://stackoverflow.com/questions/64501193/fastapi-how-to-use-httpexception-in-responses
class AuthorizationError(BaseModel):
    detail: str


class HubResponse(BaseModel):
    msg: str
    request_url: str
    token: str
    response_code: int
    hub_response: dict


class HubApiError(BaseModel):
    detail: HubResponse

class UploadRequest(BaseModel):
    file_name: str
    code: str
    type: str  # Ej.: "pub_sub", "srv", "msg", "server", "client"
