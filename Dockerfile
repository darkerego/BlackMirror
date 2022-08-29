# syntax=docker/dockerfile:1
FROM python:3.8-slim-buster
WORKDIR /opt/BlackMirror
COPY . .
RUN echo "Installing depends from apt";
RUN apt  update;
RUN apt -y upgrade;
RUN apt -y install wget build-essential python3-virtualenv;
RUN echo "Installing talib";
RUN (cd /opt; wget http://prdownloads.sourceforge.net/ta-lib/ta-lib-0.4.0-src.tar.gz; tar -xzf ta-lib-0.4.0-src.tar.gz; cd ta-lib; ./configure; make; make install);
RUN echo 'Installing BlackMirror'
RUN (cd /opt/BlackMirror; python3 -m venv env ;. env/bin/activate;pip3 install -r requirements.txt;pip install ta-lib );
RUN echo "Installing stubborn pip dependencies";
RUN (. env/bin/activate ; pip3 install websocket-client==0.37.0 websocket)
RUN echo "Done, lets see if it worked ...";
RUN (cd /opt/BlackMirror; . env/bin/activate;  ./app.py --help);
CMD ["bash", "./entry.sh"]
