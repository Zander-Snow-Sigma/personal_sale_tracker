terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 4.16"
    }
  }

  required_version = ">= 1.2.0"
}

provider "aws" {
  region  = "eu-west-2"
}

data "aws_iam_role" "ecs_task_execution_role" {
  name = "ecsTaskExecutionRole"
}


## RDS

resource "aws_db_instance" "c9-sales-tracker-db" {
  identifier = "c9-sales-tracker-db"
  allocated_storage = 20
  max_allocated_storage = 1000
  engine = "postgres"
  engine_version = "15.4"
  storage_type = "gp2"
  instance_class = "db.t3.micro"
  db_name = "c9_sales_tracker_db"
  username = var.DB_USER
  password = var.DB_PASSWORD
  port = 5432
  publicly_accessible = true
  vpc_security_group_ids = ["sg-0aa3312e61b708062"]
  db_subnet_group_name = "public_subnet_group"
  performance_insights_enabled = true
  performance_insights_retention_period = 7
  parameter_group_name = "default.postgres15"
  backup_retention_period = 1
  skip_final_snapshot = true
}

## S3 Bucket

resource "aws_s3_bucket" "c9-sale-tracker-bucket" {
  bucket = "c9-sale-tracker-bucket"
  force_destroy = true
}

resource "aws_security_group" "c9-sale-tracker-website-sg" {
  name        = "c9-sale-tracker-website-sg"
  description = "Allow TLS inbound traffic"
  vpc_id      = "vpc-04423dbb18410aece"

  ingress {
    description      = "TLS from VPC"
    from_port        = 5000
    to_port          = 5000
    protocol         = "tcp"
    cidr_blocks      = ["0.0.0.0/0"] 
  }
  egress {
    from_port        = 0
    to_port          = 0
    protocol         = "-1"
    cidr_blocks      = ["0.0.0.0/0"]
    ipv6_cidr_blocks = ["::/0"]
  }

  tags = {
    Name = "c9-sale-tracker-website-sg"
  }
}

## ECS Task Definitions

# Website/API

resource "aws_ecs_task_definition" "c9-sale-tracker-website-task-def" {
  family = "c9-sale-tracker-website-task-def"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = 1024
  memory                   = 2048
  execution_role_arn       = "${data.aws_iam_role.ecs_task_execution_role.arn}"
  container_definitions    = <<TASK_DEFINITION
[
  {
    "environment": [
      {"name": "AUTHORITY", "value": "${var.AUTHORITY}"},
      {"name": "USER_AGENT", "value": "${var.USER_AGENT}"},
      {"name": "DB_HOST", "value": "${var.DB_HOST}"},
      {"name": "DB_NAME", "value": "${var.DB_NAME}"},
      {"name": "DB_PASSWORD", "value": "${var.DB_PASSWORD}"},
      {"name": "DB_PORT", "value": "${var.DB_PORT}"},
      {"name": "DB_USER", "value": "${var.DB_USER}"},
      {"name": "AWS_ACCESS_KEY", "value": "${var.AWS_ACCESS_KEY}"},
      {"name": "AWS_SECRET_ACCESS_KEY", "value": "${var.AWS_SECRET_ACCESS_KEY}"}
    ],
    "name": "c9-sale-tracker-website",
    "image": "129033205317.dkr.ecr.eu-west-2.amazonaws.com/c9-sale-tracker-website:latest",
    "essential": true,
    "portMappings": [
      {
        "containerPort" : 5000,
        "hostPort"      : 5000
      }
    ]
  }
]
TASK_DEFINITION

  runtime_platform {
    operating_system_family = "LINUX"
    cpu_architecture        = "X86_64"
  }
}


# Dashboard

resource "aws_ecs_task_definition" "c9-sale-tracker-dashboard-task-def" {
  family = "c9-sale-tracker-dashboard-task-def"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = 1024
  memory                   = 2048
  execution_role_arn       = "${data.aws_iam_role.ecs_task_execution_role.arn}"
  container_definitions    = <<TASK_DEFINITION
[
  {
    "environment": [
      {"name": "DB_HOST", "value": "${var.DB_HOST}"},
      {"name": "DB_NAME", "value": "${var.DB_NAME}"},
      {"name": "DB_PASSWORD", "value": "${var.DB_PASSWORD}"},
      {"name": "DB_PORT", "value": "${var.DB_PORT}"},
      {"name": "DB_USER", "value": "${var.DB_USER}"}
    ],
    "name": "c9-sale-tracker-dashboard",
    "image": "",
    "essential": true
    "portMappings": [
      {
        "containerPort" : 4321,
        "hostPort"      : 4321
      }
    ]
  }
]
TASK_DEFINITION

  runtime_platform {
    operating_system_family = "LINUX"
    cpu_architecture        = "X86_64"
  }
}


# RDS Cleanup

resource "aws_ecs_task_definition" "c9-sale-tracker-rds-cleanup-task-def" {
  family = "c9-sale-tracker-rds-cleanup-task-def"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = 1024
  memory                   = 2048
  execution_role_arn       = "${data.aws_iam_role.ecs_task_execution_role.arn}"
  container_definitions    = <<TASK_DEFINITION
[
  {
    "environment": [
      {"name": "DB_HOST", "value": "${var.DB_HOST}"},
      {"name": "DB_NAME", "value": "${var.DB_NAME}"},
      {"name": "DB_PASSWORD", "value": "${var.DB_PASSWORD}"},
      {"name": "DB_PORT", "value": "${var.DB_PORT}"},
      {"name": "DB_USER", "value": "${var.DB_USER}"}
    ],
    "name": "c9-sale-tracker-rds-cleanup",
    "image": "",
    "essential": true
  }
]
TASK_DEFINITION

  runtime_platform {
    operating_system_family = "LINUX"
    cpu_architecture        = "X86_64"
  }
}


# Update Prices

resource "aws_ecs_task_definition" "c9-sale-tracker-update-prices-task-def" {
  family = "c9-sale-tracker-update-prices-task-def"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = 1024
  memory                   = 2048
  execution_role_arn       = "${data.aws_iam_role.ecs_task_execution_role.arn}"
  container_definitions    = <<TASK_DEFINITION
[
  {
    "environment": [
      {"name": "DB_HOST", "value": "${var.DB_HOST}"},
      {"name": "DB_NAME", "value": "${var.DB_NAME}"},
      {"name": "DB_PASSWORD", "value": "${var.DB_PASSWORD}"},
      {"name": "DB_PORT", "value": "${var.DB_PORT}"},
      {"name": "DB_USER", "value": "${var.DB_USER}"}
    ],
    "name": "c9-sale-tracker-update-prices",
    "image": "",
    "essential": true
  }
]
TASK_DEFINITION

  runtime_platform {
    operating_system_family = "LINUX"
    cpu_architecture        = "X86_64"
  }
}


# Price Alert

resource "aws_ecs_task_definition" "c9-sale-tracker-price-alert-task-def" {
  family = "c9-sale-tracker-price-alert-task-def"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = 1024
  memory                   = 2048
  execution_role_arn       = "${data.aws_iam_role.ecs_task_execution_role.arn}"
  container_definitions    = <<TASK_DEFINITION
[
  {
    "environment": [
      {"name": "DB_HOST", "value": "${var.DB_HOST}"},
      {"name": "DB_NAME", "value": "${var.DB_NAME}"},
      {"name": "DB_PASSWORD", "value": "${var.DB_PASSWORD}"},
      {"name": "DB_PORT", "value": "${var.DB_PORT}"},
      {"name": "DB_USER", "value": "${var.DB_USER}"},
      {"name": "SENDER_EMAIL_ADDRESS", "value": "${var.SENDER_EMAIL_ADDRESS}"},
      {"name": "AWS_ACCESS_KEY_ID", "value": "${var.AWS_ACCESS_KEY}"},
      {"name": "AWS_SECRET_ACCESS_KEY", "value": "${var.AWS_SECRET_ACCESS_KEY}"}
    ],
    "name": "c9-sale-tracker-price-alert",
    "image": "129033205317.dkr.ecr.eu-west-2.amazonaws.com/c9-sale-tracker-price-alerts:latest",
    "essential": true
  }
]
TASK_DEFINITION

  runtime_platform {
    operating_system_family = "LINUX"
    cpu_architecture        = "X86_64"
  }
}



## ECS Services

# Website/API

resource "aws_ecs_service" "c9-sale-tracker-website" {
  name            = "c9-sale-tracker-website"
  cluster         = "c9-ecs-cluster"
  task_definition = aws_ecs_task_definition.c9-sale-tracker-website-task-def.arn
  desired_count   = 1
  launch_type     = "FARGATE"
  force_new_deployment = true 
  depends_on = [aws_ecs_task_definition.c9-sale-tracker-website-task-def]

network_configuration {
    security_groups = [aws_security_group.c9-sale-tracker-website-sg.id]
    subnets         = ["subnet-0d0b16e76e68cf51b","subnet-081c7c419697dec52","subnet-02a00c7be52b00368"]
    assign_public_ip = true
  }
}

# Dashboard

resource "aws_ecs_service" "c9-sale-tracker-dash" {
  name            = "c9-sale-tracker-dash"
  cluster         = "c9-ecs-cluster"
  task_definition = aws_ecs_task_definition.c9-sale-tracker-dashboard-task-def.arn
  desired_count   = 1
  launch_type     = "FARGATE"
  force_new_deployment = true 
  depends_on = [aws_ecs_task_definition.c9-sale-tracker-dashboard-task-def]

network_configuration {
    security_groups = ["sg-020697b6514174b72"]
    subnets         = ["subnet-0d0b16e76e68cf51b","subnet-081c7c419697dec52","subnet-02a00c7be52b00368"]
    assign_public_ip = true
  }
}

## Create policy and role to allow EventBridge to trigger Step Functions

resource "aws_iam_policy" "eb_access_policy" {
  name        = "eb-access-policy"
  description = "Policy for EventBridge Scheduler to trigger Step Functions"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = [
          "states:StartExecution"
        ],
        Effect   = "Allow"
        Resource = "${aws_sfn_state_machine.c9_sale_tracker_sm.arn}"
      }
    ]
  })
}

resource "aws_iam_role" "eventbridge_scheduler_iam_role" {
  name_prefix         = "eb-scheduler-role-"
  managed_policy_arns = [aws_iam_policy.eb_access_policy.arn]
  path = "/"
  assume_role_policy  = <<EOF
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Principal": {
                "Service": "scheduler.amazonaws.com"
            },
            "Action": "sts:AssumeRole"
        }
    ]
}
EOF
}

# Create new IAM Role for Step Function

resource "aws_iam_role" "sfn_iam_role" {
  name = "sfn-iam-role"
  managed_policy_arns = ["arn:aws:iam::aws:policy/AWSStepFunctionsFullAccess"]
  assume_role_policy = <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "states.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
EOF
}


# Attach IAM Policy to Role for Step Function 

# resource "aws_iam_role_policy_attachment" "step_function_role_attachment" {
#   role       = aws_iam_role.sfn_iam_role.name
#   policy_arn = "arn:aws:iam::aws:policy/service-role/AWSStepFunctionsFullAccess"
# }


## Step Function

resource "aws_sfn_state_machine" "c9_sale_tracker_sm" {
  name = "c9-sale-tracker-sm"
  role_arn = aws_iam_role.sfn_iam_role.arn
  definition = <<EOF
{
  "Comment": "Updates the prices in the database, then alerts users if the price has changed.",
  "StartAt": "Update Prices",
  "States": {
    "Update Prices": {
      "Type": "Task",
      "Resource": "arn:aws:states:::ecs:runTask",
      "Parameters": {
        "LaunchType": "FARGATE",
        "Cluster": "arn:aws:ecs:eu-west-2:129033205317:cluster/c9-ecs-cluster",
        "TaskDefinition": "${aws_ecs_task_definition.c9-sale-tracker-update-prices-task-def.arn}"
      },
      "Next": "Price Alert"
    },
    "Price Alert": {
      "Type": "Task",
      "Resource": "arn:aws:states:::ecs:runTask",
      "Parameters": {
        "LaunchType": "FARGATE",
        "Cluster": "arn:aws:ecs:eu-west-2:129033205317:cluster/c9-ecs-cluster",
        "TaskDefinition": "${aws_ecs_task_definition.c9-sale-tracker-price-alert-task-def.arn}"
      },
      "End": true
    }
  }
}
EOF
}


## Scheduler

resource "aws_scheduler_schedule" "c9-sale-tracker-price-change-scheduler" {
  name        = "c9-sale-tracker-price-change-scheduler"

  flexible_time_window {
    mode = "OFF"
  }

  schedule_expression = "rate(3 minutes)"

  target {
    arn      = aws_sfn_state_machine.c9_sale_tracker_sm.arn
    role_arn = aws_iam_role.eventbridge_scheduler_iam_role.arn
  }
}






# Create a IAM policy that allows running ecs tasks
resource "aws_iam_policy" "ecs-schedule-permissions" {
    name = "ExecuteECSFunctions"
    policy = jsonencode({
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "ecs:RunTask"
            ],
            "Resource": [
                "${aws_ecs_task_definition.c9-sale-tracker-rds-cleanup-task-def.arn}"
            ],
            "Condition": {
                "ArnLike": {
                    "ecs:cluster": "arn:aws:ecs:eu-west-2:129033205317:cluster/c9-ecs-cluster"
                }
            }
        },
        {
            "Effect": "Allow",
            "Action": "iam:PassRole",
            "Resource": [
                "*"
            ],
            "Condition": {
                "StringLike": {
                    "iam:PassedToService": "ecs-tasks.amazonaws.com"
                }
            }
        }
    ]
})
}

# Create IAM role to attach policy to
resource "aws_iam_role" "iam_for_ecs" {
  name = "ECSPermissionsForIAM-73sfa"

  assume_role_policy = <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "ecs-tasks.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    },
    {
      "Effect": "Allow",
      "Principal": {
          "Service": "scheduler.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
      }
    ]
}
EOF
}

# Attach the IAM policy to role
resource "aws_iam_role_policy_attachment" "attach-ecs-policy" {
  role       = aws_iam_role.iam_for_ecs.name
  policy_arn = aws_iam_policy.ecs-schedule-permissions.arn
}

# Create EventBridge schedule for daily cleanup using new role
resource "aws_scheduler_schedule" "c9-sale-tracker-cleanup-schedule" {
  name        = "c9-sale-tracker-cleanup-schedule"
  group_name  = "default"

  flexible_time_window {
    maximum_window_in_minutes = 15
    mode = "FLEXIBLE"
  }
  schedule_expression_timezone = "Europe/London"
  schedule_expression = "cron(05 09 * * ? *)" 

  target {
    arn      = "arn:aws:ecs:eu-west-2:129033205317:cluster/c9-ecs-cluster"

    role_arn = aws_iam_role.iam_for_ecs.arn

    ecs_parameters {
      task_definition_arn = aws_ecs_task_definition.c9-sale-tracker-rds-cleanup-task-def.arn
      launch_type         = "FARGATE"

    network_configuration {
        subnets         = ["subnet-0d0b16e76e68cf51b","subnet-081c7c419697dec52","subnet-02a00c7be52b00368"]
        assign_public_ip = true
      }
    }
  }
}
