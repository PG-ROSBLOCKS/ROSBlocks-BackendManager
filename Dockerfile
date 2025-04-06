FROM quay.io/jupyterhub/k8s-hub:3.1.0

USER root

# Instala el cliente de Kubernetes
RUN pip install kubernetes

# Instalamos 
RUN pip install jupyter-server-proxy

# Copia tu FastAPI (si lo necesitas)
COPY ./service-fastapi /usr/src/fastapi
RUN python3 -m pip install -r /usr/src/fastapi/requirements.txt

USER ${NB_USER}
