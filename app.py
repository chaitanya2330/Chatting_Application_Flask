from flask import Flask, render_template, flash, redirect, url_for, session, request
import logging
from wtforms import Form, StringField, PasswordField, validators
from flask_mysqldb import MySQL
import os
from passlib.hash import sha256_crypt
from functools import wraps
# from flask_sqlalchemy import SQLAlchemy
from wtforms.fields.html5 import EmailField

app = Flask(__name__)
app.secret_key = os.urandom(24)
__logger = logging.getLogger(__name__)
# Config MySQL
mysql = MySQL()
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = ''
app.config['MYSQL_DB'] = ''
app.config['MYSQL_CURSORCLASS'] = 'DictCursor'

mysql.init_app(app)

class RegisterationForm(Form):
    name = StringField('Name', [validators.length(min=3, max=50)], render_kw={'autofocus': True})
    username = StringField('Username', [validators.length(min=3, max=25)])
    email = EmailField('Email', [validators.DataRequired(), validators.Email(), validators.length(min=4, max=25)])
    password = PasswordField('Password', [validators.length(min=3)])

class LoginForm(Form):
    username = StringField('Username', [validators.length(min=1)], render_kw={'autofocus': True})

class MessageForm(Form):
    body = StringField('', [validators.length(min=1)], render_kw={'autofocus': True})


def log_in(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        if 'log_in' in session:
            return f(*args, *kwargs)
        else:
            flash('Unauthorized, Please log in', 'danger')
            return redirect(url_for('login'))
    return wrap


def log_not_in(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        if 'log_in' in session:
            flash('Unauthorized, You log in', 'danger')
            return redirect(url_for('index'))
        else:
            return f(*args, *kwargs)
    return wrap


@app.route('/')
def index():
    return render_template('home.html')

# User Login
@app.route('/login', methods=['GET', 'POST'])
@log_not_in
def login():
    form = LoginForm(request.form)
    if request.method == 'POST' and form.validate():
        # GEt user form
        username = form.username.data
        password_candidate = request.form['password']

        # Create cursor
        cur = mysql.connection.cursor()

        # Get user by username
        result = cur.execute("SELECT * FROM Users WHERE username=%s", [username])

        if result > 0:
            # Get stored value
            data = cur.fetchone()
            password = data['password']
            uid = data['id']
            name = data['name']

            # Compare password
            if sha256_crypt.verify(password_candidate, password):
                # passed
                session['log_in'] = True
                session['uid'] = uid
                session['s_name'] = name
                x = '1'
                cur.execute("UPDATE Users SET online=%s WHERE id=%s", (x, uid))
                flash('You are now log in', 'success')

                return redirect(url_for('index'))

            else:
                flash('Incorrect password', 'danger')
                return render_template('login.html', form=form)

        else:
            flash('Username not found', 'danger')
            # Close connection
            cur.close()
            return render_template('login.html', form=form)
    return render_template('login.html', form=form)


@app.route('/out')
def logout():
    if 'uid' in session:

        # Create cursor
        cur = mysql.connection.cursor()
        uid = session['uid']
        x = '0'
        cur.execute("UPDATE Users SET online=%s WHERE id=%s", (x, uid))
        session.clear()
        flash('You are log out', 'success')
        return redirect(url_for('index'))
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
@log_not_in
def register():
    form = RegisterationForm(request.form)
    if request.method == 'POST' and form.validate():
        name = form.name.data
        email = form.email.data
        username = form.username.data
        password = sha256_crypt.encrypt(str(form.password.data))

        # Creating the Cursor
        cur = mysql.connection.cursor()
        cur.execute("INSERT INTO Users(name, email, username, password) VALUES(%s, %s, %s, %s)",
                    (name, email, username, password))

        # Commit the cursor
        mysql.connection.commit()

        # Close the Connection
        cur.close()

        flash('You are now registered and can login', 'success')

        return redirect(url_for('index'))
    return render_template('register.html', form=form)


@app.route('/chatting/<string:id>', methods=['GET', 'POST'])
def chatting(id):
    if 'uid' in session:
        form = MessageForm(request.form)
        # Creating the cursor
        cur = mysql.connection.cursor()

        # lid name
        get_result = cur.execute("SELECT * FROM Users WHERE id=%s", [id])
        l_data = cur.fetchone()
        if get_result > 0:
            session['name'] = l_data['name']
            uid = session['uid']
            session['lid'] = id

            if request.method == 'POST' and form.validate():
                txt_body = form.body.data

                cur = mysql.connection.cursor()
                cur.execute("INSERT INTO Message(body, msg_by, msg_to) VALUES(%s, %s, %s)",
                            (txt_body, id, uid))
                # Commit cursor
                mysql.connection.commit()

            # getting Users
            cur.execute("SELECT * FROM Users")
            users = cur.fetchall()

            # closing the connection
            cur.close()
            return render_template('chat_room.html', users=users, form=form)
        else:
            flash('No permission!', 'danger')
            return redirect(url_for('index'))
    else:
        return redirect(url_for('login'))


@app.route('/chats', methods=['GET', 'POST'])
def chats():
    if 'lid' in session:
        id = session['lid']
        uid = session['uid']
        # creating the cursor
        cur = mysql.connection.cursor()
        # Getting message
        cur.execute("SELECT * FROM Message WHERE (msg_by=%s AND msg_to=%s) OR (msg_by=%s AND msg_to=%s) "
                    "ORDER BY id ASC", (id, uid, uid, id))
        chats = cur.fetchall()
        # close the connection
        cur.close()
        return render_template('chats.html', chats=chats,)
    return redirect(url_for('login'))


if __name__ == '__main__':
    app.run(debug=True)
