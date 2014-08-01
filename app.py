# -*- coding: utf-8 -*-
import simplejson as json
import hashlib
import hmac
import os

from dropbox.client import DropboxOAuth2Flow
from flask import Flask, request, session, redirect, url_for, abort, \
    render_template, flash, jsonify
from itsdangerous import URLSafeSerializer, BadSignature
from sqlalchemy.orm.exc import NoResultFound, MultipleResultsFound

from kindlebox import emailer, kindleboxer
from kindlebox.database import db
from kindlebox.decorators import login_required_ajax
from kindlebox.models import User
from kindlebox.queue import queuefunc
import settings


DEBUG = settings.DEBUG
SECRET_KEY = settings.SECRET_KEY

DROPBOX_APP_KEY = settings.DROPBOX_APP_KEY
DROPBOX_APP_SECRET = settings.DROPBOX_APP_SECRET

app = Flask(__name__)
app.config.from_object(__name__)
app.config.from_envvar('FLASKR_SETTINGS', silent=True)
app.config['REDIS_QUEUE_KEY'] = 'dropbox_delta_users'

# Ensure instance directory exists.
try:
    os.makedirs(app.instance_path)
except OSError:
    pass


@app.route('/')
def home():
    dropbox_id = session.get('dropbox_id')
    user = User.query.filter_by(dropbox_id=dropbox_id).first()

    logged_in = dropbox_id is not None and user is not None
    kindle_name = ''
    email = ''
    active = False
    emailer = ''
    if logged_in:
        kindle_name = user.kindle_name
        email = user.email
        active = user.active
        emailer = user.emailer

    response = {
        'logged_in': logged_in,
        'kindle_name': kindle_name,
        'email': email,
        'active': active,
        'emailer': emailer,
        }
    # TODO: Display option to activate if user has a token and an
    # emailer set
    # TODO: Link to get a new emailer
    # TODO: Form to reset email address
    return render_template('index.html', **response)


@app.route('/set-user-info', methods=['POST'])
@login_required_ajax
def set_user_info(dropbox_id):
    response = {
        'success': False,
        }

    user = User.query.filter_by(dropbox_id=dropbox_id).first()
    kindle_name = request.form.get('kindle_name')

    if kindle_name is not None:
        if user.kindle_name is None:
            user.set_new_emailer()
        user.kindle_name = kindle_name
        db.commit()
        response['success'] = True
        response['emailer'] = user.emailer

    return jsonify(response)


@app.route('/login')
def login():
    # _logout()
    return redirect(get_auth_flow().start())


def _logout():
    # TODO: clear any other session args
    session.pop('dropbox_id', None)


@app.route('/logout')
def logout():
    _logout()
    return redirect(url_for('home'))


@app.route('/activate', methods=['POST'])
@login_required_ajax
def activate_user(dropbox_id):
    response = {
        'success': False,
        }

    try:
        user = User.query.filter_by(dropbox_id=dropbox_id).one()
    except NoResultFound, MultipleResultsFound:
        # TODO: log
        return jsonify(response)

    try:
        _process_user.delay(user.dropbox_id)
    except:
        # TODO: log
        return jsonify(response)

    user.activate()
    db.commit()
    response['success'] = True
    return jsonify(response)


@app.route('/dropbox-auth-finish')
def dropbox_auth_finish():
    """
    Finish Dropbox auth. If successful, user is now logged in. If the dropbox
    ID is new, register a new user.
    """
    try:
        access_token, dropbox_id, url_state = (get_auth_flow().
                                               finish(request.args))
    except DropboxOAuth2Flow.BadRequestException, e:
        abort(400)
    except DropboxOAuth2Flow.BadStateException, e:
        abort(400)
    except DropboxOAuth2Flow.CsrfException, e:
        abort(403)
    except DropboxOAuth2Flow.NotApprovedException, e:
        flash('Not approved?    Why not, bro?')
        return redirect(url_for('home'))
    except DropboxOAuth2Flow.ProviderException, e:
        app.logger.exception("Auth error" + e)
        abort(403)

    user = User.query.filter_by(dropbox_id=dropbox_id).first()
    if user is None:
        user = User(dropbox_id)
        db.add(user)

    user.access_token = access_token
    db.commit()

    session['dropbox_id'] = user.dropbox_id

    return redirect(url_for('home'))


@app.route('/dropbox-unlink')
def dropbox_unlink():
    dropbox_id = session.get('dropbox_id')
    if dropbox_id is None:
        abort(403)

    user = User.query.filter_by(dropbox_id=dropbox_id).first()
    for attribute in ['active', 'access_token', 'cursor']:
        setattr(user, attribute, None)
    db.commit()

    _logout()

    return redirect(url_for('home'))


@app.route('/dropbox-webhook', methods=['GET'])
def verify():
    if request.method != 'POST':
        return request.args.get('challenge')
    signature = request.headers.get('X-Dropbox-Signature')
    if signature != hmac.new(DROPBOX_APP_SECRET, request.data,
                             hashlib.sha256).hexdigest():
        abort(403)

    for dropbox_id in json.loads(request.data)['delta']['users']:
        _process_user.delay(dropbox_id)

    return ''


@queuefunc
def _process_user(dropbox_id):
    kindleboxer.process_user(dropbox_id)


def get_auth_flow():
    if DEBUG:
        redirect_uri = url_for('dropbox_auth_finish', _external=True)
    else:
        redirect_uri = url_for('dropbox_auth_finish', _external=True,
                _scheme="https")
    return DropboxOAuth2Flow(DROPBOX_APP_KEY, DROPBOX_APP_SECRET, redirect_uri,
                             session, 'dropbox-auth-csrf-token')


def main():
    # TODO: start a thread to read from users queue
    from kindlebox.database import init_db
    init_db()
    app.run()

if __name__ == '__main__':
    main()
