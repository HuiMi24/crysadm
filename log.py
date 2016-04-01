
from flask import render_template, session, Response
from crysadm import app, r_session
from auth import requires_auth
from datetime import datetime, timedelta
import json

@app.route('/log')
@requires_auth
def user_log():
    log_as = []
    user = session.get('user_info')
    username = user.get('username')
    key = '%s:%s' % ('user', username)
    user_data = r_session.get(key)
    user_data = json.loads(user_data.decode('utf-8'))

    if user_data.get('log_as_body') is None:
        user_data['log_as_body'] = []

    for row in user_data.get('log_as_body'):
        if (datetime.now() - datetime.strptime(row.get('time'), '%Y-%m-%d %H:%M:%S')).days < 7:
            log_as.append(row)
    log_as.reverse()

    return render_template('log.html', log_user=log_as)

@app.route('/log/delete')
@requires_auth
def user_log_delete():
    user = session.get('user_info')
    username = user.get('username')

    user['log_as_body'] = []

    r_session.set('%s:%s' % ('user', username), json.dumps(user))

    return redirect(url_for('user_log'))
