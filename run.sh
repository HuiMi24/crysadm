#!/bin/sh

ps -ef |grep -E 'crysadm'|grep -v grep|awk '{print $2}'|xargs sudo kill -9

BASE_DIR="/var/www/crysadm"

python3 ${BASE_DIR}/crysadm.py >> /var/log/crysadm.log 2>&1 &
python3 ${BASE_DIR}/crysadm_helper.py >> /var/log/crysadm.log 2>&1 &
