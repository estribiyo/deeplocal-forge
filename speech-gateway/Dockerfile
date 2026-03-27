FROM python:3.11-slim

WORKDIR /app

# Copiamos el código
COPY ./main.py ./requirements.txt .

# Instalamos dependencias mínimas
RUN pip install --no-cache-dir -r requirements.txt

# Exponemos el puerto
EXPOSE 8000

# Arrancamos con uvicorn
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
