#!/bin/bash
set -e

# Cargar ROS
source /opt/ros/jazzy/setup.bash

# Lanza el comando (por defecto, jupyterhub --ip 0.0.0.0) en segundo plano
"$@" &

# Esperar un poco
sleep 5

# Ejecutar Turtlesim en primer plano
exec ros2 run turtlesim turtlesim_node
