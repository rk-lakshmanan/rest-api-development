#!/bin/bash

if [ "$EUID" -ne 0 ]
  then echo "Please run as root"
  exit
fi

TEAMID=`md5sum README.md | cut -d' ' -f 1`
docker kill $(docker ps -q)
docker rm $(docker ps -a -q)
docker build . -t $TEAMID
#docker run -p 3306:3306 -p 80:80 -p 8080:8080 -v /home/vagrant/public/public/rest-api-development/src/html:/var/www/html -v /home/vagrant/public/public/rest-api-development/src/service:/service -t $TEAMID
docker run -p 80:80 -p 8080:8080 -v /home/vagrant/public/rest-api-development/src/html:/var/www/html -v /home/vagrant/public/rest-api-development/src/service:/service -t $TEAMID
