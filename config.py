#! /usr/bin/env python3.4
# -*- coding: utf-8 -*-
# config.py - configuration for crysadm web and redis server
__author__ = 'powergx'

DEBUG_MODE = False


def crys_log(message):
    """Automatically log the current function details."""
    import inspect
    from datetime import datetime
    func = inspect.currentframe().f_back.f_code
    if DEBUG_MODE:
        print("[%s] [%s:%s]: %s" % (datetime.now().strftime(
            '%Y-%m-%d %H:%M:%S'), func.co_name, func.co_firstlineno, message))


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
    SECRET_KEY = 'sw7dWI8l-9Tw0-rcn1-vdYM-zVWoAox5q4Il'
    REDIS_CONF = RedisConfig(host='127.0.0.1', port=6379, db=0)
    PASSWORD_PREFIX = "4kSjyQUD-rhTQ-qPkm-OvnJ-jedEdMOiONNa"
    ENCRYPT_PWD_URL = None
    SERVER_IP = '0.0.0.0'
    SERVER_PORT = 4000


class ProductionConfig(Config):
    DEBUG = False
    TESTING = False


class DevelopmentConfig(Config):
    DEBUG = True
    TESTING = False


class TestingConfig(Config):
    DEBUG = True
    TESTING = True
