FROM python:latest

COPY requirements.txt . 

EXPOSE 5000

RUN pip3 install -r requirements.txt
RUN python -m pip install 'boto3-stubs[ses]'

COPY extract.py .
COPY app.py .
COPY templates /templates


CMD python3 app.py