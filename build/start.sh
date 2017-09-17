#!/bin/bash
service nginx restart
service redis-server restart

/var/www/crysadm/run.sh
/bin/bash
