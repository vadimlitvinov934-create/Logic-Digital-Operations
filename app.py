import os
from flask import Flask, render_template, request, flash, redirect, url_for, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

app = Flask(__name__)
# Для Render берем секретный ключ из настроек, или используем дефолтный для тестов
app.secret_key = os.environ.get('SECRET_KEY', 'ldo_super_secret_key')

# Настройка БД (SQLite)
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'site.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# --- МОДЕЛИ ---
class ClientRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    contact = db.Column(db.String(100), nullable=False)
    message = db.Column(db.Text, nullable=False)
    date = db.Column(db.DateTime, default=datetime.utcnow)
    is_read = db.Column(db.Boolean, default=False)

# --- ИНИЦИАЛИЗАЦИЯ БД ---
# В Render диски очищаются при перезагрузке (на бесплатном тарифе), 
# поэтому создаем таблицы перед первым запросом, если их нет.
with app.app_context():
    db.create_all()

# --- РОУТЫ ---
@app.route('/favicon.ico')
def favicon():
    return send_from_directory(os.path.join(app.root_path, 'static'),
                               'favicon.ico', mimetype='image/vnd.microsoft.icon')

@app.route('/')
def index():
    return render_template('index.html')

# --- НОВЫЙ РОУТ: ДЕМОНСТРАЦИЯ ВОЗМОЖНОСТЕЙ ---
@app.route('/demo')
def demo():
    return render_template('demo.html')

@app.route('/submit', methods=['POST'])
def submit():
    name = request.form.get('name')
    contact = request.form.get('contact')
    message = request.form.get('message')

    if not name or not contact:
        flash('Заполните обязательные поля!', 'danger')
        return redirect(url_for('index', _anchor='contact'))

    try:
        new_req = ClientRequest(name=name, contact=contact, message=message)
        db.session.add(new_req)
        db.session.commit()
        flash('Заявка успешно отправлена! Мы свяжемся с вами.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Ошибка: {e}', 'danger')

    return redirect(url_for('index', _anchor='contact'))

@app.route('/messages')
def view_messages():
    reqs = ClientRequest.query.order_by(ClientRequest.is_read.asc(), ClientRequest.date.desc()).all()
    return render_template('messages.html', requests=reqs)

@app.route('/toggle_read/<int:request_id>', methods=['POST'])
def toggle_read(request_id):
    req = ClientRequest.query.get_or_404(request_id)
    req.is_read = not req.is_read
    db.session.commit()
    return redirect(url_for('view_messages'))

@app.route('/delete/<int:request_id>', methods=['POST'])
def delete_request(request_id):
    req = ClientRequest.query.get_or_404(request_id)
    db.session.delete(req)
    db.session.commit()
    flash('Заявка удалена', 'warning')
    return redirect(url_for('view_messages'))

if __name__ == '__main__':
    app.run(debug=True)