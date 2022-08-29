# syntax=docker/dockerfile:1
FROM python:3.8-slim-buster
WORKDIR /app
COPY . .
RUN apt  update;
RUN apt -y upgrade;
RUN apt -y install wget git build-essential;
RUN cd /opt;
RUN wget http://prdownloads.sourceforge.net/ta-lib/ta-lib-0.4.0-src.tar.gz;
RUN tar -xzf ta-lib-0.4.0-src.tar.gz;
RUN cd /opt/ta-lib;
RUN ./configure;
RUN make;
RUN make install;
RUN pip install ta-lib;
RUN pip install websocket-client==0.37.0;
RUN cd /opt;
RUN git clone https://github.com/darkerego/BlackMirror;
RUN cd BlackMirror;
RUN pip3 install -r requirements.txt
RUN ./app.py --help
CMD ["bash", "./entry.sh"]
