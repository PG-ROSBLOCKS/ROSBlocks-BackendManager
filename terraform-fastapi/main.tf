provider "aws" {
  region = "us-east-1" # Cambia si usas otra región
}

resource "aws_eks_cluster" "fastapi_eks" {
  name     = "fastapi-eks-cluster"
  role_arn = aws_iam_role.eks_role.arn

  vpc_config {
    subnet_ids = ["subnet-abc", "subnet-def"] # Sustituir con los IDs de tus subnets
  }
}

resource "aws_iam_role" "eks_role" {
  name = "eks-cluster-role"

  assume_role_policy = <<POLICY
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "eks.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
POLICY
}

resource "aws_eks_node_group" "node_group" {
  cluster_name  = aws_eks_cluster.fastapi_eks.name
  node_role_arn = aws_iam_role.eks_role.arn
  subnet_ids    = ["subnet-abc", "subnet-def"]

  scaling_config {
    desired_size = 2
    max_size     = 5
    min_size     = 1
  }
}

output "eks_cluster_endpoint" {
  value = aws_eks_cluster.fastapi_eks.endpoint
}
