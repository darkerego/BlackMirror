# syntax=docker/dockerfile:1
FROM python:3.8-slim-buster
WORKDIR /app
COPY . .
RUN pwd;ls
RUN apt  update;apt -y upgrade
RUN pip3 install -r requirements.txt

#EXPOSE 9092
CMD ["bash", "./entry.sh"]
