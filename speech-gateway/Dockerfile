FROM python:3.11-slim

WORKDIR /app

# Instalamos dependencias mínimas
RUN pip install --no-cache-dir -r requirements.txt

# Copiamos el código
COPY ./main.py .

# Exponemos el puerto
EXPOSE 8000

# Arrancamos con uvicorn
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]