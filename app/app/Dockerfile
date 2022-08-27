# syntax=docker/dockerfile:1
FROM python:3.8-slim-buster
RUN apt  update;apt -y upgrade
RUN pip3 install -r requirements.txt
COPY . . 
#EXPOSE 9092
CMD ["bash", "./entry.sh"]
