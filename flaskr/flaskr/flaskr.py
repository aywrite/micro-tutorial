from collections import namedtuple
import os
import psycopg2
from flask import (
    Flask,
    request,
    session,
    g,
    redirect,
    url_for,
    abort,
    render_template,
    flash
)

app = Flask(__name__)
app.config.from_object(__name__)

app.config.update(dict(
    DBHOST=os.getenv('PG_HOST', 'localhost'),
    DBPORT=os.getenv('PG_PORT', '5432'),
    DBNAME=os.getenv('PG_NAME', 'FLASKR'),
    DBUSER=os.getenv('PG_USER', 'postgres'),
    DBPASSWORD=os.getenv('PG_PWORD', ''),
    SECRET_KEY='DN2DaxN9LNmL85VS',
    USERNAME='admin',
    PASSWORD='default'
))
app.config.from_envvar('FLASKR_SETTINGS', silent=True)

Entry = namedtuple('entry', ['title', 'text'])

def connect_db():
    """Connects to the specific database."""
    db = psycopg2.connect(
        dbname=app.config['DBNAME'],
        user=app.config['DBUSER'],
        password=app.config['DBPASSWORD'],
        host=app.config['DBHOST'],
        port=app.config['DBPORT']
    )
    return db


def get_db():
    """Opens a new database connection if there is none yet for the
    current application context.
    """
    if not hasattr(g, 'postgres_db'):
        g.postgres_db = connect_db()
    return g.postgres_db


@app.teardown_appcontext
def close_db(error):
    """Closes the database again at the end of the request."""
    if hasattr(g, 'postgres_db'):
        g.postgres_db.close()


@app.route('/')
def show_entries():
    db = get_db()
    cur = db.cursor()
    cur.execute('select title, text from entries order by id desc')
    entries = cur.fetchall()
    entries = [Entry(*entry) for entry in entries]
    print entries
    cur.close()
    return render_template('show_entries.html', entries=entries)


@app.route('/add', methods=['POST'])
def add_entry():
    if not session.get('logged_in'):
        abort(401)
    db = get_db()
    cur = db.cursor()
    cur.execute('insert into entries (title, text) values (%s, %s)',
                 ([request.form['title'], request.form['text']]))
    db.commit()
    cur.close()
    flash('New entry was successfully posted')
    return redirect(url_for('show_entries'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        if request.form['username'] != app.config['USERNAME']:
            error = 'Invalid username'
        elif request.form['password'] != app.config['PASSWORD']:
            error = 'Invalid password'
        else:
            session['logged_in'] = True
            flash('You were logged in')
            return redirect(url_for('show_entries'))
    return render_template('login.html', error=error)


@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    flash('You were logged out')
    return redirect(url_for('show_entries'))

if __name__ == "__main__":
    app.run(debug=False, host='0.0.0.0')
