FROM python:latest

COPY requirements.txt . 

RUN pip3 install -r requirements.txt

COPY price-alert-script.py . 

CMD python3 price-alert-script.py
