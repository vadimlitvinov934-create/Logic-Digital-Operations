import os
from flask import Flask, render_template, redirect, url_for, flash, request
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SubmitField, PasswordField
from wtforms.validators import DataRequired, Length
from dotenv import load_dotenv
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from datetime import datetime

# Загружаем секреты из .env (создайте этот файл, как в прошлом шаге)
load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev_key_change_me')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///site.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# --- Модель БД (Как было у вас, но чуть лучше) ---
class ClientRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    contact = db.Column(db.String(100), nullable=False)
    message = db.Column(db.Text, nullable=False)
    date = db.Column(db.DateTime, default=datetime.utcnow)
    is_read = db.Column(db.Boolean, default=False)

# Админ (фиктивный пользователь для входа)
class AdminUser(UserMixin):
    id = 1

@login_manager.user_loader
def load_user(user_id):
    return AdminUser() if int(user_id) == 1 else None

# --- Формы ---
class LDORequestForm(FlaskForm):
    name = StringField('Имя', validators=[DataRequired()])
    contact = StringField('Контакт', validators=[DataRequired()])
    message = TextAreaField('Задача', validators=[DataRequired()])
    submit = SubmitField('Отправить заявку 🚀')

class LoginForm(FlaskForm):
    username = StringField('Login', validators=[DataRequired()])
    password = PasswordField('Pass', validators=[DataRequired()])
    submit = SubmitField('Войти')

# --- Маршруты ---

@app.route('/', methods=['GET', 'POST'])
def index():
    form = LDORequestForm()
    if form.validate_on_submit():
        new_req = ClientRequest(
            name=form.name.data,
            contact=form.contact.data,
            message=form.message.data
        )
        try:
            db.session.add(new_req)
            db.session.commit()
            flash('Заявка принята! Мы скоро свяжемся с вами.', 'success')
            return redirect(url_for('index'))
        except:
            db.session.rollback()
            flash('Ошибка базы данных.', 'error')

    return render_template('index.html', form=form)

# --- АДМИНКА (Защищена паролем) ---
@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('messages'))
    form = LoginForm()
    if form.validate_on_submit():
        if form.username.data == os.environ.get('ADMIN_USERNAME') and \
           form.password.data == os.environ.get('ADMIN_PASSWORD'):
            login_user(AdminUser())
            return redirect(url_for('messages'))
        else:
            flash('Неверный логин или пароль', 'error')
    return render_template('login.html', form=form)

@app.route('/messages')
@login_required
def messages():
    reqs = ClientRequest.query.order_by(ClientRequest.is_read.asc(), ClientRequest.date.desc()).all()
    return render_template('messages.html', requests=reqs)

@app.route('/toggle_read/<int:req_id>', methods=['POST'])
@login_required
def toggle_read(req_id):
    req = ClientRequest.query.get_or_404(req_id)
    req.is_read = not req.is_read
    db.session.commit()
    return redirect(url_for('messages'))

@app.route('/delete/<int:req_id>', methods=['POST'])
@login_required
def delete_request(req_id):
    req = ClientRequest.query.get_or_404(req_id)
    db.session.delete(req)
    db.session.commit()
    return redirect(url_for('messages'))

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)