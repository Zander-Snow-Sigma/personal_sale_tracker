# 🌐 API Pipeline Script

This folder should contain all code and resources required to run the pipeline/scraper for the SaleTracker.\
The files in this folder are used scrape information from various websites, extract, and then load it into the database.

## ⚙️ Installation and Requirements

It is recommended before stating any installations that you make a new virtual environment. 

- Install all requirements for this folder: `pip install -r requirements.txt`
- Install type hints for boto3: `python -m pip install 'boto3-stubs[ses]'`

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

### Running the API 

In order to run the API locally: `python3 app.py`. 

In order to run the API on the cloud please follow the setup instructions when creating an ECR, run the ECS task and then use the public IP address with :5000 at the end for the API to run on the cloud. 

## 🗂️ Files 

- `requirements.txt` : This file contains all the required packages to run any other files
- `Dockerfile` : This file contains instructions to create a new docker image that runs `app.py`.
- `schema.sql` : This file contains information about the database and the tables within the database. 
  - This script can be run using the command: `psql -h [DB_HOST] -p [DB_PORT] -U [DB_USER] -d [DB_NAME] -f schema.sql`.\
    - Please note you must be in the directory containing your schema in order for this to run. 
    - Please replace values in [] with the values you have in you `.env` file.
- `extract.py` : Contains code that scrapes required information from the url given in a POST request.
- `app.py` : Contains code needed to run the api and insert the required information into the RDS.
- `test_app.py` : test suite for main api file 
- `test_extract.py` : test suite for extract file

### Folders

- `templates` : Contains all of the files needed to format the API. 
- `scripts`: contains bash scripts to help run various commands in the terminal.
