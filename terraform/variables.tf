variable "DB_USER" {
  description = "Value of the username for the postgres rds instance"
  type        = string
  default = "value"
}

variable "DB_PASSWORD" {
  description = "Value of the password for the postgres rds instance"
  type        = string
  default = "value"
}
variable "DB_HOST" {
  description = "Value of the postgres rds ip"
  type        = string
  default = "value"
}

variable "DB_PORT" {
  description = "Value of the postgres rds port"
  type        = string
  default = "value"
}
variable "DB_NAME" {
  description = "Value of the database postgres rds name"
  type        = string
  default = "value"
}

variable "AWS_ACCESS_KEY" {
  description = "Value of the aws access key id"
  type        = string
  default = "value"
}

variable "AWS_SECRET_ACCESS_KEY" {
  description = "Value of the aws secret access key"
  type        = string
  default = "value"
}

variable "AUTHORITY" {
  description = "Value of the authority on the web being accessed to scrape"
  type        = string
  default = "value"
}

variable "USER_AGENT" {
  description = "Value of authority user agent"
  type        = string
  default = "value"
}

variable "SENDER_EMAIL_ADDRESS" {
  description = "Value of sender email"
  type        = string
  default = "value"
}