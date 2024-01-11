FROM python:latest

WORKDIR /dashboard

COPY requirements.txt .
RUN pip3 install -r requirements.txt

EXPOSE 8501

COPY database.py .
COPY rendering.py .
COPY visualisations.py .
COPY cookies.py .
COPY app.py .

COPY .streamlit ./.streamlit
COPY .streamlit/config.toml ./.streamlit
COPY static ./static

CMD streamlit run app.py