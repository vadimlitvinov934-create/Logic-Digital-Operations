from flask import Flask, render_template, request, flash, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import pyrebase
import requests # Добавили для Телеграма
import os

app = Flask(__name__)
app.secret_key = 'ldo_super_secret_key'

# --- НАСТРОЙКИ TELEGRAM (ЗАПОЛНИ ЭТО!) ---
# 1. Найди в Telegram бота @BotFather, создай бота, получи токен.
TELEGRAM_TOKEN = "ВАШ_ТОКЕН_ОТ_BOTFATHER"
# 2. Найди бота @userinfobot, нажми Start, он скажет твой ID (цифры).
TELEGRAM_CHAT_ID = "ВАШ_CHAT_ID"

def send_telegram_notification(name, contact, category, message):
    if "ВАШ" in TELEGRAM_TOKEN: return # Если не настроил — пропускаем
    try:
        text = f"🚀 <b>Новая заявка LDO!</b>\n\n👤 <b>Имя:</b> {name}\n📧 <b>Контакт:</b> {contact}\nBg <b>Тип:</b> {category}\n📝 <b>Сообщение:</b> {message}"
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        requests.post(url, data={"chat_id": TELEGRAM_CHAT_ID, "text": text, "parse_mode": "HTML"})
    except Exception as e:
        print(f"Ошибка отправки в TG: {e}")

# --- КОНФИГУРАЦИЯ FIREBASE ---
firebase_config = {
    "apiKey": "AIzaSyA1luUtZpTBis61nfNmluAFulH6jiYfNiE",
    "authDomain": "ldo-project-de809.firebaseapp.com",
    "projectId": "ldo-project-de809",
    "storageBucket": "ldo-project-de809.firebasestorage.app",
    "messagingSenderId": "824905447370",
    "appId": "1:824905447370:web:22d046fb6f02e8e8ec0133",
    "databaseURL": ""
}

firebase = pyrebase.initialize_app(firebase_config)
auth = firebase.auth()

# --- БАЗА ДАННЫХ ---
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

class ClientRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    contact = db.Column(db.String(100), nullable=False)
    category = db.Column(db.String(50), nullable=False)
    message = db.Column(db.Text, nullable=False)
    date = db.Column(db.DateTime, default=datetime.utcnow)
    is_read = db.Column(db.Boolean, default=False)

with app.app_context():
    db.create_all()

# --- РОУТЫ ---

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/google_auth', methods=['POST'])
def google_auth():
    data = request.get_json()
    id_token = data.get('idToken')
    email = data.get('email')
    if id_token and email:
        session['user'] = id_token
        session['email'] = email
        return {'status': 'success'}, 200
    return {'status': 'error'}, 400

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        try:
            user = auth.sign_in_with_email_and_password(email, password)
            session['user'] = user['idToken']
            flash('Вход выполнен!', 'success')
            return redirect(url_for('admin_panel'))
        except:
            flash('Ошибка входа. Проверьте данные.', 'error')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        try:
            auth.create_user_with_email_and_password(email, password)
            flash('Аккаунт создан! Теперь войдите.', 'success')
            return redirect(url_for('login'))
        except Exception as e:
            flash(f'Ошибка: {e}', 'error')
    return render_template('register.html')

@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('login'))

@app.route('/vadimadmin')
def admin_panel():
    if 'user' not in session:
        return redirect(url_for('login'))
        
    all_requests = ClientRequest.query.order_by(ClientRequest.is_read.asc(), ClientRequest.date.desc()).all()
    total = len(all_requests)
    unread = ClientRequest.query.filter_by(is_read=False).count()
    return render_template('admin.html', messages=all_requests, total=total, unread=unread)

@app.route('/contact', methods=['POST'])
def contact():
    name = request.form.get('name')
    email = request.form.get('email')
    category = request.form.get('category')
    message = request.form.get('message')

    if not name or not email:
        return redirect(url_for('home'))

    try:
        new_req = ClientRequest(name=name, contact=email, category=category, message=message)
        db.session.add(new_req)
        db.session.commit()
        
        # ОТПРАВКА В ТЕЛЕГРАМ
        send_telegram_notification(name, email, category, message)
        
        flash('Заявка отправлена! Мы скоро свяжемся с вами.', 'success')
    except Exception as e:
        flash(f'Ошибка записи: {e}', 'error')
        
    return redirect(url_for('home') + '#contact')

@app.route('/toggle_read/<int:request_id>')
def toggle_read(request_id):
    if 'user' not in session: return redirect(url_for('login'))
    req = ClientRequest.query.get_or_404(request_id)
    req.is_read = not req.is_read
    db.session.commit()
    return redirect(url_for('admin_panel'))

@app.route('/delete/<int:request_id>')
def delete_request(request_id):
    if 'user' not in session: return redirect(url_for('login'))
    req = ClientRequest.query.get_or_404(request_id)
    db.session.delete(req)
    db.session.commit()
    return redirect(url_for('admin_panel'))

if __name__ == '__main__':
    app.run(debug=True)