FROM python:latest

COPY requirements.txt . 

RUN pip3 install -r requirements.txt

COPY update_price_and_send_alerts.py . 

CMD python3 update_price_and_send_alerts.py