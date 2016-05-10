from flask import render_template, session, Response, redirect, url_for
from crysadm import app, r_session
from auth import requires_auth
from datetime import datetime, timedelta
import json


@app.route('/log')
@requires_auth
def user_log():
    log_as = []
    user = session.get('user_info')

    record_key = '%s:%s' % ('record', user.get('username'))
    if r_session.get(record_key) is None:
        return render_template('log.html', log_user=[])
    record_info = json.loads(r_session.get(record_key).decode('utf-8'))

    for row in record_info.get('diary'):
        if (datetime.now() - datetime.strptime(row.get('time'), '%Y-%m-%d %H:%M:%S')).days < 7:
            log_as.append(row)
    log_as.reverse()

    return render_template('log.html', log_user=log_as)


@app.route('/log/delete')
@requires_auth
def user_log_delete():
    user = session.get('user_info')

    record_key = '%s:%s' % ('record', user.get('username'))
    record_info = json.loads(r_session.get(record_key).decode('utf-8'))

    record_info['diary'] = []

    r_session.set(record_key, json.dumps(record_info))

    return redirect(url_for('user_log'))
    user_key = '%s:%s' % ('user', user.get('username'))
    user_info = json.loads(r_session.get(user_key).decode('utf-8'))

    user_info['log_as_body'] = []

    r_session.set('%s:%s' % ('user', username), json.dumps(user))

    return redirect(url_for('log'))
