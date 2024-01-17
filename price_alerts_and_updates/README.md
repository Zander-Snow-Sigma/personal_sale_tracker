# 💰 Price Updates Script

This folder should contain all code and resources required to run the update prices for the SaleTracker.

The files in this folder are used update the prices and stock availability of products in the RDS database, as well as alerting users in any of the following cases:

  - The product was out of stock and has gone back in stock.
  - The product was in stock and has now gone out of stock.
  - The product has decreased in price. 

## ⚙️ Installation and Requirements

It is recommended before stating any installations that you make a new virtual environment. 

- Install all requirements for this folder: `pip install -r requirements.txt`

- Create a `.env` file with `touch .env`

### Required env variables

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

### Running the script 

In order to run the API locally : `python3 update_price_and_send_alert.py`. 


## 🗂️ Files 

- `requirements.txt` : This file contains all the required packages to run any other files
- `Dockerfile` : This file contains instructions to create a new docker image that runs `app.py`.
- `update_price_and_send_alert.py` : Contains code needed to update the product prices and alert the user of any changes. insert the required information into the RDS.
- `price_alert_logs.log` : Contains logs of any price or stock changes. 

### Folders

- `templates` : Contains all of the files needed to format the API. 
- `scripts`: contains bash scripts to help run various commands in the terminal.
