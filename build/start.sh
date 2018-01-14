#!/bin/bash
service nginx restart
service redis-server restart
sleep 3
BASE_DIR="/var/www/crysadm/"

python3 ${BASE_DIR}/crysadm_helper.py >> /var/log/uwsgi/crysadm_uwsgi.log 2>&1 &
uwsgi --ini /var/www/crysadm/crysadm_uwsgi.ini >> /var/log/uwsgi/crysadm_uwsgi.log 2>&1 &
tail -f /var/log/uwsgi/crysadm_uwsgi.log 
