# syntax=docker/dockerfile:1
FROM python:3.8-slim-buster
WORKDIR /app
COPY . .
RUN apt  update;apt -y upgrade; apt -y install wget git build-essential
RUN cd /opt; wget http://prdownloads.sourceforge.net/ta-lib/ta-lib-0.4.0-src.tar.gz; tar -xzf ta-lib-0.4.0-src.tar.gz
RUN cd /opt/ta-lib; ./configure; make; make install
RUN cd /opt; git clone https://darkerego/blackmirror; cd BlackMirror; pip3 install -r requirements.txt
CMD ["bash", "./entry.sh"]
