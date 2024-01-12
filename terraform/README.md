# 🔧 Terraform
This folder should contain all code and resources required to handle the infrastructure of the project.

## ⚙️ Installation and Requirements

`.tfvars` keys used:

- `USER_AGENT` : A request header is a characteristic string that lets servers and network peers identify the application, operating system, vendor, and/or version of the requesting user agent.
  - e.g. `"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3"`
- `DB_USER` : The user name to login to the database.
- `DB_PASSWORD` : The password to login to the database.
- `DB_PORT` : The port you are using.
- `DB_HOST` : The host name or address of a database server.
- `DB_NAME` : The name of your database.
- `AWS_ACCESS_KEY_ID` : An access key id from AWS.
- `AWS_SECRET_ACCESS_KEY` : A secret key associated with the above identifier, serving as a password. 
- `SENDER_EMAIL_ADDRESS` : The email address to send user alerts from.

## 🏃 Running the script

Run the terraform with `terraform init` and then `terraform apply`.
Remove the terraform with `terraform destroy`

## 🗂️ Files Explained
- `main.tf`
    - A terraform script to create all resources and services needed within the project. These services include:
      - `RDS Database`
        - An RDS instance to hold all of the relevant data.
      - `Website Security Group`
        - Security group allowing traffic from everywhere to access the website via port 5000.
      - `Dashboard Security Group`
        - Security group allowing traffic from everywhere to access the dashboard via port 8501.  
      - `Website Task Definition`
        - Task definition to run the website container found in AWS ECR.
      - `Dashboard Task Definition`
        - Task definition to run the dashboard container found in AWS ECR.  
      - `Price Updates Task Definition`
        - Task definition to run the price updates container found in AWS ECR.  
      - `Website ECS Service`
         - ECS Service that constantly runs the website task and makes it publicly available on the cloud.
      - `Dashboard ECS Service`
         - ECS Service that constantly runs the dashboard task and makes it publicly available on the cloud.   
      - `load old data Task Definition`
         - Task definition to run the load old data container found in AWS ECR.
      - `EventBridge Scheduler`
         - EventBridge Scheduler that executes the price updates task every 3 mins.
