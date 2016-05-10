__author__ = 'powergx'
import config, socket, redis
from login import login
from datetime import datetime, timedelta
from multiprocessing import Process
from multiprocessing.dummy import Pool as ThreadPool
import threading
from api import *
import logging


conf = config.TestingConfig

redis_conf = conf.REDIS_CONF
pool = redis.ConnectionPool(host=redis_conf.host, port=redis_conf.port, db=redis_conf.db, password=redis_conf.password)
r_session = redis.Redis(connection_pool=pool)


# 获取用户数据
def get_data(username):
    config.crys_log('get %s data' % username)

    start_time = datetime.now()
    try:
        for user_id in r_session.smembers('accounts:%s' % username):
            time.sleep(3)
            account_key = 'account:%s:%s' % (username, user_id.decode('utf-8'))
            account_info = json.loads(r_session.get(account_key).decode('utf-8'))

            # clean the log everyday
            record_key = '%s:%s' % ('record', username)
            if start_time.hour == 23 and start_time.minute >= 55:
                record_info = dict(diary=[])
                r_session.set(record_key, json.dumps(record_info))

            if not account_info.get('active'):
                continue

            config.crys_log('start get data with user id %s ' % user_id)

            session_id = account_info.get('session_id')
            user_id = account_info.get('user_id')
            cookies = dict(sessionid=session_id, userid=str(user_id))

            mine_info = get_mine_info(cookies)
            if is_api_error(mine_info):
                config.crys_log('get data %s error#' % user_id)
                #if DEBUG_MODE:
                #    print('get_data:', user_id, mine_info, 'error')
                return

            if mine_info.get('r') != 0:

                success, account_info = __relogin(account_info.get('account_name'), account_info.get('password'),
                                                  account_info, account_key)
                if not success:
                    config.crys_log('%s re-login failed' % user_id)
                    print('get_data:', user_id, 'relogin failed')
                    continue
                session_id = account_info.get('session_id')
                user_id = account_info.get('user_id')
                cookies = dict(sessionid=session_id, userid=str(user_id))
                mine_info = get_mine_info(cookies)

            if mine_info.get('r') != 0:
                config.crys_log('get mime info %s error#' % user_id)
                #print('get_data:', user_id, mine_info, 'error')
                continue

            device_info = ubus_cd(session_id, user_id, 'get_devices', ["server", "get_devices", {}])
            red_zqb = device_info['result'][1]

            account_data_key = account_key + ':data'
            exist_account_data = r_session.get(account_data_key)
            if exist_account_data is None:
                account_data = dict()
                account_data['privilege'] = get_privilege(cookies)
            else:
                account_data = json.loads(exist_account_data.decode('utf-8'))

            if account_data.get('updated_time') is not None:
                last_updated_time = datetime.strptime(account_data.get('updated_time'), '%Y-%m-%d %H:%M:%S')
                if last_updated_time.hour != datetime.now().hour:
                    account_data['zqb_speed_stat'] = get_speed_stat(cookies)
            else:
                account_data['zqb_speed_stat'] = get_speed_stat(cookies)

            account_data['updated_time'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            account_data['mine_info'] = mine_info
            account_data['device_info'] = red_zqb.get('devices')
            account_data['income'] = get_income_info(cookies)
            account_data['produce_info'] = get_produce_stat(cookies)

            if is_api_error(account_data.get('income')):
                config.crys_log('get income %s error#' % user_id)
                #print('get_data:', user_id, 'income', 'error')
                return

            r_session.set(account_data_key, json.dumps(account_data))
            if not r_session.exists('can_drawcash'):
                r = get_can_drawcash(cookies=cookies)
                if r.get('r') == 0:
                    r_session.setex('can_drawcash', r.get('is_tm'), 60)

        if start_time.day == datetime.now().day:
            save_history(username)

        r_session.setex('user:%s:cron_queued' % username, '1', 60)
        if DEBUG_MODE:
            config.crys_log('get data user %s successed#' % username)
            #print(datetime.now().strftime('%Y-%m-%d %H:%M:%S'), username.encode('utf-8'), 'successed')
    except Exception as ex:
        config.crys_log('get data user %s failed##' % username)
        print(username.encode('utf-8'), 'failed', datetime.now().strftime('%Y-%m-%d %H:%M:%S'), ex)


# 保存历史数据
def save_history(username):
    #
    #if DEBUG_MODE:
    #    print(datetime.now().strftime('%Y-%m-%d %H:%M:%S'), 'save_history')
    str_today = datetime.now().strftime('%Y-%m-%d')
    key = 'user_data:%s:%s' % (username, str_today)
    b_today_data = r_session.get(key)
    today_data = dict()

    if b_today_data is not None:
        today_data = json.loads(b_today_data.decode('utf-8'))

    today_data['updated_time'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    today_data['pdc'] = 0
    today_data['last_speed'] = 0
    today_data['deploy_speed'] = 0
    today_data['balance'] = 0
    today_data['income'] = 0
    today_data['speed_stat'] = list()
    today_data['pdc_detail'] = []
    today_data['giftbox_pdc'] = 0
    today_data['produce_stat'] = []
    today_data['award_income'] = 0

    for user_id in r_session.smembers('accounts:%s' % username):
        # 获取账号所有数据
        account_data_key = 'account:%s:%s:data' % (username, user_id.decode('utf-8'))
        b_data = r_session.get(account_data_key)
        if b_data is None:
            continue
        data = json.loads(b_data.decode('utf-8'))

        if datetime.strptime(data.get('updated_time'), '%Y-%m-%d %H:%M:%S') + timedelta(minutes=1) < datetime.now() or \
                             datetime.strptime(data.get('updated_time'), '%Y-%m-%d %H:%M:%S').day != datetime.now().day:
            continue
        today_data.get('speed_stat').append(dict(mid=data.get('privilege').get('mid'),
                                                 dev_speed=data.get('zqb_speed_stat') if data.get(
                                                     'zqb_speed_stat') is not None else [0] * 24))
        this_pdc = data.get('mine_info').get('dev_m').get('pdc')

        today_data['pdc'] += this_pdc
        today_data.get('pdc_detail').append(dict(mid=data.get('privilege').get('mid'), pdc=this_pdc))

        today_data['balance'] += data.get('income').get('r_can_use')
        today_data['income'] += data.get('income').get('r_h_a')
        today_data['giftbox_pdc'] += data.get('mine_info').get('td_box_pdc')
        today_data.get('produce_stat').append(
            dict(mid=data.get('privilege').get('mid'), hourly_list=data.get('produce_info').get('hourly_list')))
        if data.get('award_income') is not None:
            today_data['award_income'] += getaward_crystal_income(username, user_id.decode('utf-8'))
        today_data['pdc'] += today_data['award_income']
        for device in data.get('device_info'):
            today_data['last_speed'] += int(int(device.get('dcdn_upload_speed')) / 1024)
            today_data['deploy_speed'] += int(device.get('dcdn_download_speed') / 1024)
    r_session.setex(key, json.dumps(today_data), 3600 * 24 * 35)
    save_income_history(username, today_data.get('pdc_detail'))


# 获取保存的历史数据
def save_income_history(username, pdc_detail):
    #
    #if DEBUG_MODE:
    #    print(datetime.now().strftime('%Y-%m-%d %H:%M:%S'), username.encode('utf-8'), 'save_income_history')
    now = datetime.now()
    key = 'user_data:%s:%s' % (username, 'income.history')
    b_income_history = r_session.get(key)
    income_history = dict()

    if b_income_history is not None:
        income_history = json.loads(b_income_history.decode('utf-8'))

    if now.minute < 50:
        return

    if income_history.get(now.strftime('%Y-%m-%d')) is None:
        income_history[now.strftime('%Y-%m-%d')] = dict()

    income_history[now.strftime('%Y-%m-%d')][now.strftime('%H')] = pdc_detail

    r_session.setex(key, json.dumps(income_history), 3600 * 72)


# 重新登录
def __relogin(username, password, account_info, account_key):
    config.crys_log('')#
    #if DEBUG_MODE:
    #    print(datetime.now().strftime('%Y-%m-%d %H:%M:%S'), username.encode('utf-8'), 'relogin')

    login_result = login(username, password, conf.ENCRYPT_PWD_URL)

    if login_result.get('errorCode') != 0:
        account_info['status'] = login_result.get('errorDesc')
        account_info['active'] = False
        r_session.set(account_key, json.dumps(account_info))
        return False, account_info

    account_info['session_id'] = login_result.get('sessionID')
    account_info['status'] = 'OK'
    r_session.set(account_key, json.dumps(account_info))
    return True, account_info


# 获取在线用户数据
def get_online_user_data():
    config.crys_log('')#
    #if DEBUG_MODE:
    #    print(datetime.now().strftime('%Y-%m-%d %H:%M:%S'), 'get_online_user_data')
    if r_session.exists('api_error_info'): return

    pool = ThreadPool(processes=1)

    pool.map(get_data, (u.decode('utf-8') for u in r_session.smembers('global:online.users')))
    pool.close()
    pool.join()


# 获取离线用户数据
def get_offline_user_data():
    config.crys_log('')
    #if DEBUG_MODE:
    #    print(datetime.now().strftime('%Y-%m-%d %H:%M:%S'), 'get_offline_user_data')
    if r_session.exists('api_error_info'): return
    if datetime.now().minute < 50: return

    offline_users = []
    for b_user in r_session.mget(*['user:%s' % name.decode('utf-8') for name in
                                   r_session.sdiff('users', *r_session.smembers('global:online.users'))]):
        user_info = json.loads(b_user.decode('utf-8'))

        username = user_info.get('username')

        if not user_info.get('active'): continue

        every_hour_key = 'user:%s:cron_queued' % username
        if r_session.exists(every_hour_key): continue

        offline_users.append(username)

    pool = ThreadPool(processes=5)

    pool.map(get_data, offline_users)
    pool.close()
    pool.join()


# 从在线用户列表中清除离线用户
def clear_offline_user():
    if DEBUG_MODE:
        print(datetime.now().strftime('%Y-%m-%d %H:%M:%S'), 'clear_offline_user')
    for b_username in r_session.smembers('global:online.users'):
        username = b_username.decode('utf-8')
        if not r_session.exists('user:%s:is_online' % username):
            r_session.srem('global:online.users', username)


# 刷新选择自动任务的用户
def select_auto_task_user():
    if DEBUG_MODE:
        print(datetime.now().strftime('%Y-%m-%d %H:%M:%S'), 'select_auto_task_user')
    auto_collect_accounts = []
    auto_drawcash_accounts = []
    auto_giftbox_accounts = []
    auto_searcht_accounts = []
    auto_revenge_accounts = []
    auto_getaward_accounts = []
    auto_detect_accounts = []
    for b_user in r_session.mget(*['user:%s' % name.decode('utf-8') for name in r_session.smembers('users')]):
        user_info = json.loads(b_user.decode('utf-8'))
        if not user_info.get('active'): continue
        username = user_info.get('username')
        account_keys = ['account:%s:%s' % (username, user_id.decode('utf-8')) for user_id in
                        r_session.smembers('accounts:%s' % username)]
        if len(account_keys) == 0: continue
        for b_account in r_session.mget(*account_keys):
            account_info = json.loads(b_account.decode('utf-8'))
            if not (account_info.get('active')): continue
            session_id = account_info.get('session_id')
            user_id = account_info.get('user_id')
            cookies = json.dumps(dict(sessionid=session_id, userid=user_id, user_info=user_info))
            if user_info.get('auto_collect'): auto_collect_accounts.append(cookies)
            if user_info.get('auto_drawcash'): auto_drawcash_accounts.append(cookies)
            if user_info.get('auto_giftbox'): auto_giftbox_accounts.append(cookies)
            if user_info.get('auto_searcht'): auto_searcht_accounts.append(cookies)
            if user_info.get('auto_revenge'): auto_revenge_accounts.append(cookies)
            if user_info.get('auto_getaward'): auto_getaward_accounts.append(cookies)
            if user_info.get('auto_detect'): auto_detect_accounts.append(cookies)
    r_session.delete('global:auto.collect.cookies')
    if len(auto_collect_accounts) != 0:
        r_session.sadd('global:auto.collect.cookies', *auto_collect_accounts)
    r_session.delete('global:auto.drawcash.cookies')
    if len(auto_drawcash_accounts) != 0:
        r_session.sadd('global:auto.drawcash.cookies', *auto_drawcash_accounts)
    r_session.delete('global:auto.giftbox.cookies')
    if len(auto_giftbox_accounts) != 0:
        r_session.sadd('global:auto.giftbox.cookies', *auto_giftbox_accounts)
    r_session.delete('global:auto.searcht.cookies')
    if len(auto_searcht_accounts) != 0:
        r_session.sadd('global:auto.searcht.cookies', *auto_searcht_accounts)
    r_session.delete('global:auto.revenge.cookies')
    if len(auto_revenge_accounts) != 0:
        r_session.sadd('global:auto.revenge.cookies', *auto_revenge_accounts)
    r_session.delete('global:auto.getaward.cookies')
    r_session.sadd('global:auto.getaward.cookies', *auto_getaward_accounts)
    r_session.delete('global:auto.detect.cookies')
    r_session.sadd('global:auto.detect.cookies', *auto_detect_accounts)


# 执行检测异常矿机函数
def detect_exception(user, cookies, user_info):
    from mailsand import send_email
    print(datetime.now().strftime('%Y-%m-%d %H:%M:%S'), 'detect_exception')
    config_key = '%s:%s' % ('user', 'system')
    config_info = json.loads(r_session.get(config_key).decode('utf-8'))
    account_data_key = 'account:%s:%s:data' % (user_info.get('username'), user.get('userid'))
    user_key = '%s:%s' % ('user', user_info.get('username'))
    user_info = json.loads(r_session.get(user_key).decode('utf-8'))
    exist_account_data = r_session.get(account_data_key)
    if exist_account_data is None: return
    account_data = json.loads(exist_account_data.decode('utf-8'))
    if not 'device_info' in account_data.keys(): return
    need_clear = True
    last_exception_key = 'last_exception:%s' % user.get('userid')
    if 'detect_info' not in user_info.keys():
        detect_info = {}
    else:
        detect_info = user_info['detect_info']
    for dev in account_data['device_info']:
        if dev['status'] != 'online':
            status_cn = {'offline': '离线', 'online': '在线', 'exception': '异常'}
            if last_exception_key in detect_info.keys():
                last_time = datetime.strptime(detect_info[last_exception_key], '%Y-%m-%d %H:%M:%S')
                if (datetime.now() - last_time).seconds > 30:
                    if 'last_warn' not in detect_info.keys() or (
                        datetime.now() - datetime.strptime(detect_info['last_warn'],
                                                           '%Y-%m-%d %H:%M:%S')).seconds > 60 * 60:
                        if 'warn_reset' not in detect_info.keys() or detect_info['warn_reset']:
                            if validateEmail(user_info['mail_address']) == 1:
                                mail = dict()
                                mail['to'] = user_info['mail_address']
                                mail['subject'] = '云监工-矿机异常'
                                mail['text'] = ''.join(
                                    ['您的矿机：', dev['device_name'], '<br />状态：', status_cn[dev['status']], '<br />时间：',
                                     datetime.now().strftime('%Y-%m-%d %H:%M:%S')])
                                send_email(mail, config_info)
                                detect_info['warn_reset'] = False
                                detect_info['last_warn'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            else:
                red_log(user, '矿机异常', '状态', '%s:%s -> %s' % (dev['device_name'], '在线', status_cn[dev['status']]))
                detect_info[last_exception_key] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            need_clear = False
        if 'dcdn_clients' in dev.keys():
            for i, client in enumerate(dev['dcdn_clients']):
                if ('space_%s:%s' % (i, user.get('userid'))) in detect_info.keys():
                    last_space = detect_info['space_%s:%s:%s' % (i, user.get('userid'), dev['device_name'])]
                    if last_space - 100 * 1024 * 1024 > int(client['space_used']):
                        red_log(user, '缓存变动', '状态', '%s: %.2fGB -> %.2fGB' % (
                        dev['device_name'], float(last_space) / 1024 / 1024 / 1024,
                        float(client['space_used']) / 1024 / 1024 / 1024))
                        detect_info['space_%s:%s:%s' % (i, user.get('userid'), dev['device_name'])] = int(
                            client['space_used'])
                    elif last_space < int(client['space_used']):
                        detect_info['space_%s:%s:%s' % (i, user.get('userid'), dev['device_name'])] = int(
                            client['space_used'])
                else:
                    detect_info['space_%s:%s:%s' % (i, user.get('userid'), dev['device_name'])] = int(
                        client['space_used'])
    if need_clear == True:
        detect_info['warn_reset'] = True
        detect_info.pop(last_exception_key, '^.^')
    user_info['detect_info'] = detect_info
    r_session.set(user_key, json.dumps(user_info))


# 执行收取水晶函数
def check_collect(user, cookies, user_info):
    if DEBUG_MODE:
        print(datetime.now().strftime('%Y-%m-%d %H:%M:%S'), 'check_collect')
    mine_info = get_mine_info(cookies)
    time.sleep(2)
    if mine_info.get('r') != 0: return
    if 'collect_crystal_modify' in user_info.keys():
        limit = user_info.get('collect_crystal_modify')
    else:
        limit = 16000;

    if mine_info.get('td_not_in_a') > limit:
        r = collect(cookies)
        if r.get('rd') != 'ok':
            log = '%s' % r.get('rd')
        else:
            log = '收取:%s水晶.' % mine_info.get('td_not_in_a')
        red_log(user, '自动执行', '收取', log)
    time.sleep(3)


# 执行自动提现的函数
def check_drawcash(user, cookies, user_info):
    if DEBUG_MODE:
        print(datetime.now().strftime('%Y-%m-%d %H:%M:%S'), 'check_drawcash')
    if 'draw_money_modify' in user_info.keys():
        limit = user_info.get('draw_money_modify')
    else:
        limit = 10.0
    r = exec_draw_cash(cookies=cookies, limits=limit)
    red_log(user, '自动执行', '提现', r.get('rd'))
    time.sleep(3)


# 执行免费宝箱函数
def check_giftbox(user, cookies, user_info):
    if DEBUG_MODE:
        print(datetime.now().strftime('%Y-%m-%d %H:%M:%S'), 'check_giftbox')
    box_info = api_giftbox(cookies)
    time.sleep(2)
    if box_info.get('r') != 0: return
    for box in box_info.get('ci'):
        if box.get('cnum') == 0:
            r_info = api_openStone(cookies=cookies, giftbox_id=box.get('id'), direction='3')
            if r_info.get('r') != 0:
                log = r_info.get('rd')
            else:
                r = r_info.get('get')
                log = '开启:获得:%s水晶.' % r.get('num')
        else:
            r_info = api_giveUpGift(cookies=cookies, giftbox_id=box.get('id'))
            if r_info.get('r') != 0:
                log = r_info.get('rd')
            else:
                log = '丢弃:收费:%s水晶.' % box.get('cnum')
        red_log(user, '自动执行', '宝箱', log)
    time.sleep(3)


# 执行秘银进攻函数
def check_searcht(user, cookies, user_info):
    if DEBUG_MODE:
        print(datetime.now().strftime('%Y-%m-%d %H:%M:%S'), 'check_searcht')
    r = api_sys_getEntry(cookies)
    time.sleep(2)
    if r.get('r') != 0: return
    if r.get('steal_free') > 0:
        steal_info = api_steal_search(cookies)
        if steal_info.get('r') != 0:
            log = regular_html(r.get('rd'))
        else:
            time.sleep(3)
            t = api_steal_collect(cookies=cookies, searcht_id=steal_info.get('sid'))
            if t.get('r') != 0:
                log = 'Forbidden'
            else:
                log = '获得:%s秘银.' % t.get('s')
                time.sleep(1)
                api_steal_summary(cookies=cookies, searcht_id=steal_info.get('sid'))
        red_log(user, '自动执行', '进攻', log)
    time.sleep(3)


# 执行秘银复仇函数
def check_revenge(user, cookies, user_info):
    print(datetime.now().strftime('%Y-%m-%d %H:%M:%S'), 'check_revenge')
    r = api_steal_stolenSilverHistory(cookies)
    time.sleep(2)
    if r.get('r') != 0: return
    for q in r.get('list'):
        if q.get('st') == 0:
            steal_info = api_steal_search(cookies, q.get('sid'))
            if steal_info.get('r') != 0:
                log = regular_html(r.get('rd'))
            else:
                time.sleep(3)
                t = api_steal_collect(cookies=cookies, searcht_id=steal_info.get('sid'))
                if t.get('r') != 0:
                    log = 'Forbidden'
                else:
                    log = '获得:%s秘银.' % t.get('s')
                    time.sleep(1)
                    api_steal_summary(cookies=cookies, searcht_id=steal_info.get('sid'))
            red_log(user, '自动执行', '复仇', log)
    time.sleep(3)


# get award income from log
def getaward_crystal_income(username, user_id):
    if DEBUG_MODE:
        print(datetime.now().strftime('%Y-%m-%d %H:%M:%S'), 'getaward_crystal_income')
    today_award_income = 0
    str_today = datetime.now().strftime('%Y-%m-%d')
    key = '%s:%s' % ('record', username)
    b_user_data = r_session.get(key)
    if b_user_data is not None:
        user_data = json.loads(b_user_data.decode('utf-8'))
    else:
        return today_award_income
    if user_data.get('diary') is not None:
        user_log = user_data.get('diary')
    else:
        return today_award_income
    for item in user_log:
        now = datetime.now()
        log_time = datetime.strptime(item.get('time'), '%Y-%m-%d %H:%M:%S')
        if log_time.day == now.day and user_id == item.get('id'):
            today_award_income += check_award_income(item.get('gets'))
    time.sleep(3)
    return today_award_income


# 执行幸运转盘函数
def check_getaward(user, cookies, user_info):
    if DEBUG_MODE:
        print(datetime.now().strftime('%Y-%m-%d %H:%M:%S'), 'check_getaward')
    r = api_getconfig(cookies)
    time.sleep(2)
    if r.get('rd') != 'ok': return
    if r.get('cost') == 5000:
        t = api_getaward(cookies)
        if t.get('rd') != 'ok':
            log = t.get('rd')
        else:
            log = '获得:%s' % regular_html(t.get('tip'))
        red_log(user, '自动执行', '转盘', log)

    time.sleep(3)
    return r


# 收取水晶
def collect_crystal():
    if DEBUG_MODE:
        print(datetime.now().strftime('%Y-%m-%d %H:%M:%S'), 'collect_crystal')

    cookies_auto(check_collect, 'global:auto.collect.cookies')


#    for cookie in r_session.smembers('global:auto.collect.cookies'):
#        check_collect(json.loads(cookie.decode('utf-8')))

# 自动提现
def drawcash_crystal():
    if DEBUG_MODE:
        print(datetime.now().strftime('%Y-%m-%d %H:%M:%S'), 'drawcash_crystal')
    time_now = datetime.now()
    if int(time_now.isoweekday()) != 2: return
    if int(time_now.hour) < 11 or int(time_now.hour) > 18: return

    cookies_auto(check_drawcash, 'global:auto.drawcash.cookies')


#    for cookie in r_session.smembers('global:auto.drawcash.cookies'):
#        check_drawcash(json.loads(cookie.decode('utf-8')))

# 免费宝箱
def giftbox_crystal():
    if DEBUG_MODE:
        print(datetime.now().strftime('%Y-%m-%d %H:%M:%S'), 'giftbox_crystal')

    cookies_auto(check_giftbox, 'global:auto.giftbox.cookies')


#    for cookie in r_session.smembers('global:auto.giftbox.cookies'):
#        check_giftbox(json.loads(cookie.decode('utf-8')))

# 秘银进攻
def searcht_crystal():
    if DEBUG_MODE:
        print(datetime.now().strftime('%Y-%m-%d %H:%M:%S'), 'searcht_crystal')
    cookies_auto(check_searcht, 'global:auto.searcht.cookies')


#    for cookie in r_session.smembers('global:auto.searcht.cookies'):
#        check_searcht(json.loads(cookie.decode('utf-8')))

# 秘银复仇
def revenge_crystal():
    print(datetime.now().strftime('%Y-%m-%d %H:%M:%S'), 'revenge_crystal')

    cookies_auto(check_revenge, 'global:auto.revenge.cookies')


# 幸运转盘
def getaward_crystal():
    if DEBUG_MODE:
        print(datetime.now().strftime('%Y-%m-%d %H:%M:%S'), 'getaward_crystal')

    cookies_auto(check_getaward, 'global:auto.getaward.cookies')


#    for cookie in r_session.smembers('global:auto.getaward.cookies'):
#        check_getaward(json.loads(cookie.decode('utf-8')))

# 自动监测
def auto_detect():
    print(datetime.now().strftime('%Y-%m-%d %H:%M:%S'), 'auto_detect')

    cookies_auto(detect_exception, 'global:auto.detect.cookies')


#    for cookie in r_session.smembers('global:auto.getaward.cookies'):
#        check_getaward(json.loads(cookie.decode('utf-8')))


# 处理函数[重组]
def cookies_auto(func, cookiename):
    if DEBUG_MODE:
        print(datetime.now().strftime('%Y-%m-%d %H:%M:%S'), 'execute %s' % str(func))
    users = r_session.smembers(cookiename)
    if users is not None and len(users) > 0:
        for user in users:
            try:
                cookies = json.loads(user.decode('utf-8'))
                session_id = cookies.get('sessionid')
                user_id = cookies.get('userid')
                user_info = cookies.get('user_info')
                func(cookies, dict(sessionid=session_id, userid=user_id), user_info)
            except Exception as e:
                continue


# 正则过滤+URL转码
def regular_html(info):
    import re
    from urllib.parse import unquote
    regular = re.compile('<[^>]+>')
    url = unquote(info)
    return regular.sub("", url)


def validateEmail(email):
    import re
    if len(email) > 7:
        if re.match("^.+\\@(\\[?)[a-zA-Z0-9\\-\\.]+\\.([a-zA-Z]{2,3}|[0-9]{1,3})(\\]?)$", email) != None:
            return 1
    return 0


# 自动日记记录
def red_log(cook, clas, type, gets):
    user = cook.get('user_info')

    record_key = '%s:%s' % ('record', user.get('username'))
    if r_session.get(record_key) is None:
        record_info = dict(diary=[])
    else:
        record_info = json.loads(r_session.get(record_key).decode('utf-8'))

    id = cook.get('userid')

    log_as_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    body = dict(time=log_as_time, clas=clas, type=type, id=id, gets=gets)

    log_as_body = record_info.get('diary')
    log_as_body.append(body)

    record_info['diary'] = log_as_body

    r_session.set(record_key, json.dumps(record_info), 3600 * 24)


# 计时器函数，定期执行某个线程，时间单位为秒
def timer(func, seconds):
    while True:
        Process(target=func).start()
        time.sleep(seconds)


if __name__ == '__main__':
    config_key = '%s:%s' % ('user', 'system')
    r_config_info = r_session.get(config_key)
    if r_config_info is None:
        config_info = {
            'collect_crystal_interval': 30 * 60,
            'drawcash_crystal_interval': 60 * 60,
            'giftbox_crystal_interval': 40 * 60,
            'searcht_crystal_interval': 360 * 60,
            'revenge_crystal_interval': 300 * 60,
            'getaward_crystal_interval': 240 * 60,
            'get_online_user_data_interval': 30,
            'get_offline_user_data_interval': 600,
            'clear_offline_user_interval': 60,
            'select_auto_task_user_interval': 10 * 60,
            'auto_detect_interval': 5 * 60,
            'master_mail_smtp': 'smtp.163.com',
            'master_mail_address': 'xxxxxxxx@163.com',
            'master_mail_password': 'xxxxxxxxxxxxxx',
        }
        r_session.set(config_key, json.dumps(config_info))
    else:
        config_info = json.loads(r_config_info.decode('utf-8'))
    # 执行收取水晶时间，单位为秒，默认为30秒。
    # 每30分钟检测一次收取水晶
    threading.Thread(target=timer, args=(collect_crystal, config_info['collect_crystal_interval'])).start()
    # 执行自动提现时间，单位为秒，默认为60秒。
    # 每60分钟检测一次自动提现
    threading.Thread(target=timer, args=(drawcash_crystal, config_info['drawcash_crystal_interval'])).start()
    # 执行免费宝箱时间，单位为秒，默认为40秒。
    # 每40分钟检测一次免费宝箱
    threading.Thread(target=timer, args=(giftbox_crystal, config_info['giftbox_crystal_interval'])).start()
    # 执行秘银进攻时间，单位为秒，默认为360秒。
    # 每360分钟检测一次秘银进攻
    threading.Thread(target=timer, args=(searcht_crystal, config_info['searcht_crystal_interval'])).start()
    # 执行秘银复仇时间，单位为秒，默认为300秒。
    # 每300分钟检测一次秘银复仇
    threading.Thread(target=timer, args=(revenge_crystal, config_info['revenge_crystal_interval'])).start()
    # 执行幸运转盘时间，单位为秒，默认为240秒。
    # 每240分钟检测一次幸运转盘
    threading.Thread(target=timer, args=(getaward_crystal, config_info['getaward_crystal_interval'])).start()
    # 执行自动监测时间，单位为秒，默认为300秒。
    # 每5分钟检测一次矿机状态
    threading.Thread(target=timer, args=(auto_detect, config_info['auto_detect_interval'])).start()
    # 刷新在线用户数据，单位为秒，默认为30秒。
    # 每30秒刷新一次在线用户数据
    threading.Thread(target=timer, args=(get_online_user_data, config_info['get_online_user_data_interval'])).start()
    # 刷新离线用户数据，单位为秒，默认为60秒。
    # 每10分钟刷新一次离线用户数据
    threading.Thread(target=timer, args=(get_offline_user_data, config_info['get_offline_user_data_interval'])).start()
    # 从在线用户列表中清除离线用户，单位为秒，默认为60秒。
    # 每分钟检测离线用户
    threading.Thread(target=timer, args=(clear_offline_user, config_info['clear_offline_user_interval'])).start()
    # 刷新选择自动任务的用户，单位为秒，默认为10分钟
    threading.Thread(target=timer, args=(select_auto_task_user, config_info['select_auto_task_user_interval'])).start()
    while True:
        time.sleep(1)
