FROM python:3.13-slim

WORKDIR /app

COPY . .

RUN mkdir -p /app/storage

EXPOSE 3000
EXPOSE 5000

CMD ["python", "main.py"]