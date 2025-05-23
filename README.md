# ROSBlocks BackendManager

**ROSBlocks BackendManager** is a FastAPI-based utility designed to manage the dynamic deployment of user-specific ROSBlocks environments in AWS using ECS Fargate. This service handles the orchestration of backend container instances, mapping users to private IPs, and managing task lifecycles (start, stop, and cleanup).

While most of the infrastructure setup (IAM roles, ECS cluster, task definitions, networking) was configured manually through the AWS Console, this repository contains the core logic that enables:

- Starting a new ECS task when a user connects
- Tracking and mapping each user to their assigned container's private IP
- Stopping the ECS task and releasing resources when the session ends
- Ensuring session isolation across concurrent users

## Key Features

- FastAPI-based service to control ECS deployments
- Integration with AWS SDK (boto3) to manage ECS tasks
- Private IP assignment and user-session tracking
- Lightweight and scalable API server for managing runtime containers
- Session TTL support for automatic cleanup of stale sessions

## Project Structure

- **main.py** – Entry point for the FastAPI application
- **requirements.txt** – Python dependencies (including FastAPI and boto3)
- **fastapi.service** – Service for executing fastapi in an EC2 instance
- **nginx.conf** – Testing configuration file of nginx

## Prerequisites

- An existing ECS Cluster configured with:
  - Task definitions for the ROSBlocks environment
  - Proper IAM roles with ECS and EC2 permissions
  - Networking (VPC, Subnets, Security Groups) allowing container access
- Python 3.8+ and `pip`
- AWS credentials configured locally or via environment variables

## Installation

Clone the repository:

```bash
git clone https://github.com/PG-ROSBLOCKS/BackendManager.git
cd BackendManager
```

Install dependencies:

```bash
pip install -r requirements.txt
```

## Running the BackendManager

You can start the FastAPI server locally for development or debugging purposes:

```bash
uvicorn main:app --host 0.0.0.0 --port 8001 --reload
```

## Notes

- This repository does not include the frontend or the actual ROS 2 containers.
- All infrastructure (cluster, networking, IAM) is assumed to be pre-configured via the AWS Console.
- The service is stateless beyond session mapping; it is recommended to add persistent session storage or monitoring for production deployments.

