FROM python:3.10-slim

ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Copiar solo lo necesario (requirements primero para cache)
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# Copiar la app
COPY app /app/app

# No copiar .env ni venv
EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]



