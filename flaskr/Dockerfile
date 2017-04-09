FROM ubuntu:latest
RUN apt-get update -y
RUN apt-get install -y python-pip python-dev build-essential
COPY . /app
WORKDIR /app
RUN pip install -r requirements.txt
ENV PG_USER='postgres'
ENV PG_PWORD=''
ENV PG_PORT=5432
ENV PG_NAME='postgres'
ENTRYPOINT ["python"]
CMD ["flaskr/flaskr.py"]

