__author__ = 'powergx'


class RedisConfig():
    def __init__(self, host, port, db, password=None):
        self.host = host
        self.port = port
        self.db = db
        self.password = password


class Config(object):
    DEBUG = False
    TESTING = False
    DATABASE_URI = ''
    ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif'}
    SESSION_TYPE = 'memcached'
    SECRET_KEY = '4kSjyQUD-rhTQ-qPkm-OvnJ-jedEdMOiONNa'
    REDIS_CONF = RedisConfig(host='127.0.0.1', port=6379, db=0)
    PASSWORD_PREFIX = "4kSjyQUD-rhTQ-qPkm-OvnJ-jedEdMOiONNa"
    ENCRYPT_PWD_URL = None
    SERVER_IP = '127.0.0.1'
    SERVER_PORT = 5000


class ProductionConfig(Config):
    DEBUG = True


class DevelopmentConfig(Config):
    DEBUG = True


class TestingConfig(Config):
    DEBUG = True
    TESTING = True