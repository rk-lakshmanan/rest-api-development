#!/bin/bash

chown -R mysql:mysql /var/lib/mysql /var/run/mysqld
service mysql start
apachectl start
python /service/app.py
