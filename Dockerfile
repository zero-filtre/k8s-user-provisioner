FROM python:3.8

WORKDIR /app

COPY requirements.txt /app/
COPY . /app/

RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 5000

ENTRYPOINT ["sh", "-c", "source /vault/secrets/config && python run.py"]