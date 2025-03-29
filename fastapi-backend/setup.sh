#!/bin/bash

set -e

# Instalar Python y herramientas necesarias
sudo apt update
sudo apt install -y python3 python3-venv python3-pip

# Crear entorno virtual
python3 -m venv venv
source venv/bin/activate

# Instalar dependencias
pip install -r requirements.txt

echo "✅ FastAPI backend instalado"
