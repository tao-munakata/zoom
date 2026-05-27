FROM mcr.microsoft.com/playwright/python:v1.44.0-jammy

RUN apt-get update && apt-get install -y \
    xvfb x11vnc novnc websockify \
    ffmpeg pulseaudio pulseaudio-utils \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
RUN chmod +x entrypoint.sh

ENTRYPOINT ["/bin/bash", "entrypoint.sh"]
