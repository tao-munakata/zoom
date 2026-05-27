FROM ubuntu:22.04
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y ffmpeg && rm -rf /var/lib/apt/lists/*
COPY extract.sh /extract.sh
RUN chmod +x /extract.sh
CMD ["/extract.sh"]
