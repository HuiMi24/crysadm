#!/bin/sh

ps -ef | grep -E 'crysadm.*(py|ini)' | grep -v grep  | awk '{print $2}'| xargs kill

BASE_DIR="/var/www/crysadm"

python3 ${BASE_DIR}/crysadm_helper.py >> /var/log/uwsgi/crysadm_uwsgi.log 2>&1 &
uwsgi --ini /var/www/crysadm/crysadm_uwsgi.ini >> /var/log/uwsgi/crysadm_uwsgi.log 2>&1 &
