FROM ubuntu:latest
RUN apt-get update
RUN apt-get install -y python-pip
RUN apt-get install -y apache2
RUN apt-get install -y vim
RUN apt-get install -y build-essential libffi-dev
RUN pip install -U pip
RUN pip install -U flask
RUN pip install -U flask-cors
RUN pip install flask-sqlalchemy
RUN pip install flask_marshmallow
RUN pip install bcrypt
RUN pip install marshmallow-sqlalchemy

RUN echo "ServerName localhost  " >> /etc/apache2/apache2.conf
RUN echo "$user     hard    nproc       20" >> /etc/security/limits.conf

ADD ./src/service /service
ADD ./src/html /var/www/html
EXPOSE 80
EXPOSE 8080

CMD ["/bin/bash", "/service/start_services.sh"]
