# syntax=docker/dockerfile:1
FROM python:3.8-slim-buster
WORKDIR /opt/BlackMirror
COPY . .
RUN echo "Installing depends from apt";
RUN apt  update;
RUN apt -y upgrade;
RUN apt -y install wget git build-essential python3-virtualenv;
RUN echo "Installing talib";
RUN (cd /opt; wget http://prdownloads.sourceforge.net/ta-lib/ta-lib-0.4.0-src.tar.gz; tar -xzf ta-lib-0.4.0-src.tar.gz; cd ta-lib; ./configure; make; make install);
RUN echo 'Installing BlackMirror'
RUN pip3 install virtualenv websocket-client==0.37.0
RUN (cd /opt; git clone https://github.com/darkerego/BlackMirror; cd BlackMirror; python3 -m venv env; source env/bin/activate; pip3 install -r requirements.txt; pip install websocket-client==0.37.0; pip install ta-lib );
RUN echo "Installing stubborn pip dependencies";
RUN pip3 install websocket-client==0.37.0
RUN echo "Done, lets see if it worked ...";
RUN (cd /opt/BlackMirror; ./app.py --help);
CMD ["bash", "./entry.sh"]
