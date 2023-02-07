FROM python:3.11.1-slim

COPY requirements.txt /app/requirements.txt
WORKDIR /app

RUN pip install -r requirements.txt

COPY . /app

CMD ["python","-m", "wsc_spot_poll"]