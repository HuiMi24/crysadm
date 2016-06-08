#声明
云监工的原作者是powergx，有很多功能也是从别人那里merge过来的。我只是加了一些自己想要的功能。

# 云监工配置Nginx、uWSGI

## 安装Nginx和uWSGI

```bash
sudo apt-get install nginx
sudo python3.4 -m pip install uwsgi
```

##配置Nginx
创建云监工存放目录/var/www/crysadm
```bash
sudo mkdir /var/www
sudo mkdir /var/www/crysadm
```
由于是用root创建的，在这里需要修改目录权限。我用的是树莓派，所以需要改成pi:pi
```bash
sudo chown -R pi:pi /var/www/crysadm
```
首先删除Nginx默认的配置文件
```bash
sudo rm /etc/nginx/sites-enabled/default
```
配置文件已上传，不感兴趣的可以直接跳到最后一步

创建云监工使用的配置文件/var/www/crysadm/crysadm_nginx.conf
```shell
server {
    listen      4000;
    server_name 0.0.0.0;
    charset     utf-8;
    client_max_body_size 75M;

    location / { try_files $uri @yourapplication; }
    location @yourapplication {
        include uwsgi_params;
        uwsgi_pass unix:/var/www/crysadm/crysadm_uwsgi.sock;
    }
}
```
将配置文件符号链接到Nginx配置文件目录，重启Nginx
```bash
sudo ln -s /var/www/crysadm/crysadm_nginx.conf /etc/nginx/conf.d/
sudo /etc/init.d/nginx restart
```
##配置uWSGI
创建一个新的uWSGI配置文件/var/www/crysadm/crysadm_uwsgi.ini
```bash
[uwsgi]
#application's base folder
base = /var/www/crysadm

#python module to import
app = crysadm
module = %(app)

#home = %(base)/
pythonpath = %(base)

#socket file's location
socket = /var/www/crysadm/%n.sock

#permissions for the socket file
chmod-socket    = 666

#the variable that holds a flask application inside the module imported at line #6
callable = app

#location of log files
logto = /var/log/uwsgi/%n.log
```
创建uWSGI存放log目录，并修改权限
```bash
sudo mkdir -p /var/log/uwsgi
sudo chown -R pi:pi /var/log/uwsgi
```
##克隆云监工代码
```bash
cd /var/www/
git clone https://github.com/HuiMi24/crysadm.git
```
如果你是第一次部署，首先要启动redis-server
```bash
sudo /etc/init.d/redis-server start
```
运行云监工
```bash
sudo /var/www/crysadm/run.sh
```

可以通过浏览器访问云监工了，默认的使用的端口是4000

127.0.0.1:4000
