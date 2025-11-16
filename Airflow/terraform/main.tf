# airflow/terraform/main.tf
terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 4.0"
    }
  }
}

provider "aws" {
  region = "us-east-1"
  
  # Para AWS Academy - usar el LabRole
  assume_role {
    role_arn = "arn:aws:iam::${var.account_id}:role/LabRole"
  }
}

variable "account_id" {
  description = "Tu AWS Account ID de Academy"
  type        = string
}

# ECR Repository
resource "aws_ecr_repository" "airflow" {
  name = "alerta-utec-airflow"
}

# ECS Cluster
resource "aws_ecs_cluster" "airflow" {
  name = "alerta-utec-airflow-cluster"
}

# ECS Task Definition - USANDO ROLES EXISTENTES de Academy
resource "aws_ecs_task_definition" "airflow" {
  family                   = "airflow-task"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = "1024"
  memory                   = "2048"
  
  # En Academy, usa los roles que YA existen
  execution_role_arn = "arn:aws:iam::${var.account_id}:role/ecsTaskExecutionRole"
  task_role_arn      = "arn:aws:iam::${var.account_id}:role/EC2ContainerServiceTaskRole"

  container_definitions = jsonencode([{
    name  = "airflow"
    image = "${aws_ecr_repository.airflow.repository_url}:latest"
    portMappings = [{
      containerPort = 8080
      hostPort      = 8080
    }]
    environment = [
      { name = "AIRFLOW__CORE__EXECUTOR", value = "LocalExecutor" },
      { name = "AIRFLOW__CORE__LOAD_EXAMPLES", value = "false" },
      { name = "AIRFLOW__CORE__DAGS_ARE_PAUSED_AT_CREATION", value = "false" }
    ]
    logConfiguration = {
      logDriver = "awslogs"
      options = {
        awslogs-group         = "/ecs/airflow"
        awslogs-region        = "us-east-1"
        awslogs-stream-prefix = "ecs"
      }
    }
  }])
}

# ECS Service - VPC SIMPLIFICADA para Academy
resource "aws_ecs_service" "airflow" {
  name            = "airflow-service"
  cluster         = aws_ecs_cluster.airflow.id
  task_definition = aws_ecs_task_definition.airflow.arn
  desired_count   = 1
  launch_type     = "FARGATE"

  network_configuration {
    # Usar subnets por defecto de Academy
    subnets          = data.aws_subnets.default.ids
    security_groups  = [aws_security_group.airflow.id]
    assign_public_ip = true  # ← Necesario en Academy para acceso
  }
}

# Data sources para recursos por defecto de Academy
data "aws_vpc" "default" {
  default = true
}

data "aws_subnets" "default" {
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.default.id]
  }
}

# Security Group simplificado
resource "aws_security_group" "airflow" {
  name        = "airflow-sg"
  description = "Security group for Airflow"
  vpc_id      = data.aws_vpc.default.id

  ingress {
    description = "Airflow Web UI"
    from_port   = 8080
    to_port     = 8080
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]  # Temporal para demo
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "airflow-sg"
  }
}

# CloudWatch Log Group
resource "aws_cloudwatch_log_group" "airflow" {
  name              = "/ecs/airflow"
  retention_in_days = 7
}
