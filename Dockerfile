FROM resin/rpi-raspbian
MAINTAINER humi <mihui24@gmail.com>
RUN apt-get update \
        && apt-get install -y nginx redis-server python3 git vim curl gcc build-essential python3-dev sudo\
        && rm -rf /var/lib/apt/lists/*

RUN curl --silent --show-error --retry 5 https://bootstrap.pypa.io/get-pip.py | python3 \
        && python3 -m pip install flask requests redis uwsgi

RUN mkdir -p /var/www/crysadm \
        && mkdir -p /var/log/uwsgi \
        && cd /var/www \
        && git clone https://github.com/HuiMi24/crysadm.git \
        && cd crysadm \
        && mv /etc/nginx/sites-enabled/default . \
        && ln -s /var/www/crysadm/crysadm_nginx.conf /etc/nginx/conf.d/ \
        && rm /etc/localtime \
        && ln -s /usr/share/zoneinfo/Asia/Shanghai /etc/localtime 

VOLUME /var/lib/redis

EXPOSE 80
EXPOSE 4000
EXPOSE 22
WORKDIR /var/www/crysadm

RUN touch /start.sh \
        && chmod +x /start.sh \
        && echo "#!/bin/bash" >> /start.sh \
        && echo "service nginx restart" >> /start.sh \
        && echo "service redis-server restart" >> /start.sh \
        && echo "/var/www/crysadm/run.sh" >> /start.sh \
        && echo "/bin/bash" >> /start.sh
