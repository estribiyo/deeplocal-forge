FROM python:3.11-slim
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libopenblas-dev \  
    libatomic1 \
    git \
    && rm -rf /var/lib/apt/lists/*
COPY main.py requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
EXPOSE 10400 10420
CMD python3 -m wyoming_openwakeword --uri 'tcp://0.0.0.0:10400' --preload-model 'hey_jarvis' --preload-model 'alexa' --threshold 0.3 --trigger-level 1 --debug & \ 
    python3 main.py
