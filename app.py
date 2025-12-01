from flask import Flask, render_template, request, flash, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'ldo_super_secret_key'

# --- НАСТРОЙКА БАЗЫ ДАННЫХ ---
# Файл базы данных site.db создастся сам в папке проекта
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Создаем модель (таблицу) для хранения заявок
class ClientRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)   # Имя
    contact = db.Column(db.String(100), nullable=False) # Контакт
    message = db.Column(db.Text, nullable=False)        # Сообщение
    date = db.Column(db.DateTime, default=datetime.utcnow) # Дата и время

    def __repr__(self):
        return f'<Заявка {self.id} от {self.name}>'

# Эта команда создает файл базы данных, если его нет
with app.app_context():
    db.create_all()


@app.route('/')
def index():
    return render_template('index.html')

@app.route('/submit', methods=['POST'])
def submit():
    if request.method == 'POST':
        name = request.form.get('name')
        contact = request.form.get('contact')
        message = request.form.get('message')

        # Проверка, чтобы не отправляли пустые поля
        if not name or not contact:
            flash('Пожалуйста, заполните имя и контакт!', 'error')
            return redirect(url_for('index'))

        # --- СОХРАНЕНИЕ В БАЗУ ---
        try:
            new_request = ClientRequest(name=name, contact=contact, message=message)
            db.session.add(new_request) # Добавляем
            db.session.commit()         # Сохраняем
            
            flash('Заявка успешно улетела в базу LDO! Ждите ответа.', 'success')
        except Exception as e:
            flash(f'Ошибка базы данных: {e}', 'error')
            
        return redirect(url_for('index'))

# --- СЕКРЕТНАЯ АДМИНКА ---
# Перейди на http://127.0.0.1:5000/messages чтобы увидеть заявки
@app.route('/messages')
def view_messages():
    # Достаем все заявки из базы, новые сверху
    all_requests = ClientRequest.query.order_by(ClientRequest.date.desc()).all()
    
    # Простой вывод прямо в браузер (для теста)
    html = "<h1>Входящие заявки LDO</h1><hr>"
    for req in all_requests:
        html += f"""
            <div style="background:#f0f0f0; padding:10px; margin-bottom:10px; border-radius:10px; font-family:sans-serif;">
                <strong>От:</strong> {req.name} <br>
                <strong>Связь:</strong> {req.contact} <br>
                <strong>Сообщение:</strong> {req.message} <br>
                <small style="color:gray;">{req.date}</small>
            </div>
        """
    return html

if __name__ == '__main__':
    app.run(debug=True)