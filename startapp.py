# -*- coding: utf-8 -*-

import os
import posixpath
import constants
import database
from sqlite3 import dbapi2 as sqlite3
from flask import Flask, request, session, g, redirect, url_for, abort, \
     render_template, flash, _app_ctx_stack

from dropbox.client import DropboxClient, DropboxOAuth2Flow

# configuration
DEBUG = True
DATABASE = 'myapp.db'
SECRET_KEY = 'development key'

# Fill these in!
DROPBOX_APP_KEY = constants.DROPBOX_APP_KEY
DROPBOX_APP_SECRET = constants.DROPBOX_APP_SECRET

# create our little application :)
app = Flask(__name__)
app.config.from_object(__name__)
app.config.from_envvar('FLASKR_SETTINGS', silent=True)

# Ensure instance directory exists.
try:
    os.makedirs(app.instance_path)
except OSError:
    pass

db = None

def init_db():
    """Creates the database tables."""
    with app.app_context():
        global db
        db = database.Database(app)
        storage = db.get_db()
        with app.open_resource("schema.sql", mode="r") as f:
            storage.cursor().executescript(f.read())
        storage.commit()

@app.route('/', methods = ['GET', 'POST'])
def home():
    if 'user' not in session:
        return redirect(url_for('login'))

    real_name = None
    access_token = get_access_token()
    print(access_token)
    folder = get_folder()
    print(folder)

    #user not active
    if access_token is None:
        return render_template('index.html', real_name=real_name, folder = folder)

    client = DropboxClient(access_token)
    account_info = client.account_info()
    real_name = account_info['display_name']

    if folder:
        contents = get_books_from_folder(client, folder)
        return render_template('index.html', real_name="You are logged in as " + real_name, folder = folder,
            folder_contents = contents)

    return render_template('index.html', real_name="You are logged in as " + real_name, folder = folder)

@app.route('/dropbox-auth-finish')
def dropbox_auth_finish():
    username = session.get('user')
    if username is None:
        abort(403)
    try:
        access_token, user_id, url_state = get_auth_flow().finish(request.args)
    except DropboxOAuth2Flow.BadRequestException, e:
        abort(400)
    except DropboxOAuth2Flow.BadStateException, e:
        abort(400)
    except DropboxOAuth2Flow.CsrfException, e:
        abort(403)
    except DropboxOAuth2Flow.NotApprovedException, e:
        flash('Not approved?  Why not, bro?')
        return redirect(url_for('home'))
    except DropboxOAuth2Flow.ProviderException, e:
        app.logger.exception("Auth error" + e)
        abort(403)
    data = [access_token, username]
    db.write('UPDATE users SET active = 1, access_token = ? WHERE kindle_name = ?', data)
    return redirect(url_for('home'))

@app.route('/dropbox-auth-start')
def dropbox_auth_start():
    if 'user' not in session:
        abort(403)
    return redirect(get_auth_flow().start())

@app.route('/dropbox-unlink')
def dropbox_unlink():
    username = session.get('user')
    if username is None:
        abort(403)
    db.write('UPDATE users SET access_token = NULL, folder = NULL, \
        email_address = NULL, active = 0 WHERE kindle_name = ?', [username])
    return redirect(url_for('home'))

def get_auth_flow():
    redirect_uri = url_for('dropbox_auth_finish', _external=True)
    return DropboxOAuth2Flow(DROPBOX_APP_KEY, DROPBOX_APP_SECRET, redirect_uri,
                                       session, 'dropbox-auth-csrf-token')

@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        kindlename = request.form['kindlename']
        if kindlename:
            session['user'] = kindlename
            active = db.readRow('SELECT active FROM users WHERE kindle_name = ?', [kindlename])
            if active == 0 or active == None:
                db.write('INSERT OR IGNORE INTO users (kindle_name, active) \
                    VALUES (?)', [kindlename])
                return redirect(url_for('dropbox_auth_start'))
            else:
                return redirect(url_for('home'))
    return render_template('login.html', error=error)

@app.route('/logout')
def logout():
    session.pop('user', None)
    flash('You were logged out')
    return redirect(url_for('home'))


def set_active():
    username = session.get('user')
    if username is None:
        return None
    return db.write('UPDATE users SET active = 1 WHERE kindle_name = ?', [username])

def get_access_token():
    username = session.get('user')
    if username is None:
        return None
    return db.readRow('SELECT access_token FROM users WHERE kindle_name = ?', [username])

def get_folder():
    username = session.get('user')
    if username is None:
        return None
    if request.method == 'POST':
        folder = request.form['folder']
        set_folder(folder)
    return db.readRow('SELECT folder FROM users WHERE kindle_name = ?', [username])

def set_folder(folder):
    username = session.get('user')
    if username is None:
        return None
    db.write('UPDATE users SET folder = ? WHERE kindle_name = ?', [folder, username])

def get_books_from_folder(client, folder):
    metadata = client.metadata(folder)
    books = []
    for f in metadata['contents']:
        if f['is_dir']:
            books += get_books_from_folder(client, f['path'])
        else:
            books.append(f['path'])
    return books


def main():
    init_db()
    app.run()

if __name__ == '__main__':
    main()
