FROM ubuntu:latest
RUN apt-get update
RUN apt-get install -y python-pip
RUN apt-get install -y apache2
RUN DEBIAN_FRONTEND=noninteractive apt-get -y install libmysqlclient-dev
RUN pip install -U pip
RUN pip install -U flask
RUN pip install -U flask-cors
RUN pip install flask-sqlalchemy
RUN pip install mysqlclient
RUN echo "ServerName localhost  " >> /etc/apache2/apache2.conf
RUN echo "$user     hard    nproc       20" >> /etc/security/limits.conf

RUN DEBIAN_FRONTEND=noninteractive apt-get -y install mysql-server
RUN mkdir /var/run/mysqld

ADD ./src/service /service
ADD ./src/html /var/www/html
EXPOSE 80
EXPOSE 8080
EXPOSE 3306
CMD ["mysqld"]
CMD ["/bin/bash", "/service/start_services.sh"]
