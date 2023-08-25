FROM python:3.8

WORKDIR /app

COPY requirements.txt /app/
COPY . /app/

RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 5000

RUN chmod 755 entrypoint.sh

ENTRYPOINT ["./entrypoint.sh"]