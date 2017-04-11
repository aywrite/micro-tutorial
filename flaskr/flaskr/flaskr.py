from collections import namedtuple
import os
import requests
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
from py_zipkin.zipkin import zipkin_span

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
    PASSWORD='default',
    ZP_HOST=os.getenv('ZP_HOST', 'localhost')
))
app.config.from_envvar('FLASKR_SETTINGS', silent=True)

Entry = namedtuple('entry', ['title', 'text'])


def http_transport(encoded_span):
    # The collector expects a thrift-encoded list of spans. Instead of
    # decoding and re-encoding the already thrift-encoded message, we can just
    # add header bytes that specify that what follows is a list of length 1.
    host = ''.join(['http://', app.config['ZP_HOST'], r':9411/api/v1/spans'])
    body = '\x0c\x00\x00\x00\x01' + encoded_span
    requests.post(
        host,
        data=body,
        headers={'Content-Type': 'application/x-thrift'},
    )


def init_db():
    db = get_db()
    cur = db.cursor()
    cur.execute(
        """CREATE TABLE entries (
        id serial PRIMARY KEY,
        title text NOT NULL,
        text text NOT NULL);
        """
    )
    db.commit()
    cur.close()


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
    with zipkin_span(
        service_name='default',
        span_name='entries_endpoint',
        transport_handler=http_transport,
        sample_rate=100, # Value between 0.0 and 100.0
    ):
        entries = get_entries()
        return render_template('show_entries.html', entries=entries)


@zipkin_span(service_name='default', span_name='get_entries')
def get_entries(limit=10):
    db = get_db()
    cur = db.cursor()
    cur.execute('SELECT title, text FROM entries ORDER BY id DESC LIMIT (%s)',
                ([limit]))
    entries = cur.fetchall()
    entries = [Entry(*entry) for entry in entries]
    cur.close()
    return entries


def format_entries(entries):
    formated_entries = []
    for entry in entries:
        new_entry = Entry(entry.title.title(), entry.text)
        formated_entries.append(new_entry)
    return new_entry


@app.route('/add', methods=['POST'])
def add_entry():
    with zipkin_span(
        service_name='default',
        span_name='add_entry_endpoint',
        transport_handler=http_transport,
        sample_rate=100
    ):
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
