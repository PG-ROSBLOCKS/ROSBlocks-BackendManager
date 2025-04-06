FROM quay.io/jupyterhub/jupyterhub

# Create test user (PAM auth) and install single-user Jupyter
RUN useradd testuser --create-home --shell /bin/bash
RUN echo 'testuser:passwd' | chpasswd
RUN pip install jupyter

RUN python3 -m pip install --no-cache-dir \
    dockerspawner \
    jupyterhub-nativeauthenticator

COPY app ./app
COPY jupyterhub_config.py .
COPY requirements.txt /tmp/requirements.txt
RUN pip install -r /tmp/requirements.txt

CMD ["jupyterhub", "--ip", "0.0.0.0"]
