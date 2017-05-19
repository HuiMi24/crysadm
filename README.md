# 2017/05/19
增加Dockerfile，可以自行根据Dockerfile构建image,/var/lib/redis是外卷，用于存放数据库。内部nginx的端口为4000。
Note: 我自己用的是树莓派，所以base是resin/rpi-raspbian。如果你使用的是x86的机器，直接修改为ubuntu就可以了。

## 1.安装docker
    请自行baidu
## 2.build image
```bash
    mkdir images
    cp Dockerfile images/
    sudo docker build -t crysadm .
```
## 3.执行
```bash
    sudo docker run -itd -p 80:4000 -v /var/lib/redis:/var/lib/redis crysadm /start.sh
```

# 2017/03/28
修复第一次安装之后数据不显示的bug，简化安装教程。
# 2016/12/15
新增上传总量统计。

# 2016/12/13
迅雷最近似乎更改了API，现在不能通过原有api获取速度信息。现在改为没30.0s获取一次数据，来计算每个小时的平均速度，数据不一定非常准确，但有一定参考性。
# 声明
云监工的原作者是powergx，有很多功能也是从别人那里merge过来的。我只是加了一些自己想要的功能。

如果没有重大bug，此版本将不再更新。如果你发现bug，或者有新的功能，可以提交pull request。

# 云监工配置

```bash
sudo apt-get install nginx redis-server -y
sudo python3.4 -m pip install uwsgi flask requests redis
```
创建云监工存放目录/var/www/crysadm
```bash
sudo mkdir /var/www
sudo mkdir /var/www/crysadm
```
由于是用root创建的，在这里需要修改目录权限。我用的是树莓派，所以需要改成pi:pi
```bash
sudo chown -R pi:pi /var/www/crysadm
```
## 克隆云监工代码
```bash
cd /var/www/
git clone https://github.com/HuiMi24/crysadm.git
```
## 配置Nginx, Uwsig

首先删除Nginx默认的配置文件
```bash
sudo rm /etc/nginx/sites-enabled/default
```
将配置文件符号链接到Nginx配置文件目录，重启Nginx
```bash
sudo ln -s /var/www/crysadm/crysadm_nginx.conf /etc/nginx/conf.d/
sudo /etc/init.d/nginx restart
```
创建uWSGI存放log目录，并修改权限
```bash
sudo mkdir -p /var/log/uwsgi
sudo chown -R pi:pi /var/log/uwsgi
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

访问127.0.0.1:4000/install 生成管理员账号密码，只有一次机会。如果忘了，把数据库数据删除重新加载这个页面。

