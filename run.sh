#!/bin/sh

ps -ef |grep python | grep -E 'crysadm'|grep -v grep|awk '{print $2}'|xargs sudo kill -9

BASE_DIR="/var/www/crysadm"

python3.4 ${BASE_DIR}/crysadm_helper.py >> /var/log/uwsgi/crysadm_uwsgi.log 2>&1 &
uwsgi --ini /var/www/crysadm/crysadm_uwsgi.ini >> /var/log/uwsgi/crysadm_uwsgi.log 2>&1 &
