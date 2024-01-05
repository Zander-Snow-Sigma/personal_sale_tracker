FROM python:latest

COPY requirements.txt . 

RUN pip3 install -r requirements.txt

COPY price_alert_script.py . 

CMD python3 price_alert_script.py
