from flask import Flask, render_template, request, flash, redirect, url_for, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import os 

app = Flask(__name__)
app.secret_key = 'ldo_super_secret_key'

# --- НАСТРОЙКА БАЗЫ ДАННЫХ ---
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Создаем модель (таблицу) для хранения заявок
class ClientRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)    # Имя
    contact = db.Column(db.String(100), nullable=False) # Контакт
    message = db.Column(db.Text, nullable=False)        # Сообщение
    date = db.Column(db.DateTime, default=datetime.utcnow) # Дата и время
    # Добавим поле 'is_read' для отметки о прочтении, по умолчанию False (непрочитано)
    is_read = db.Column(db.Boolean, default=False) 

    def __repr__(self):
        return f'<Заявка {self.id} от {self.name}>'

# Эта команда создает файл базы данных, если его нет
with app.app_context():
    db.create_all()


# --- РОУТ ДЛЯ ФАВИКОНА (ОБЕСПЕЧИВАЕТ КОРРЕКТНУЮ ЗАГРУЗКУ) ---
@app.route('/favicon.ico')
def favicon():
    # Файл favicon.ico будет искаться в папке /static
    return send_from_directory(os.path.join(app.root_path, 'static'),
                              'favicon.ico',
                              mimetype='image/vnd.microsoft.icon')
# -----------------------------------------------------------


@app.route('/')
def index():
    # В шаблоне index.html нужно предусмотреть отображение flash-сообщений
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
            db.session.rollback()
            flash(f'Ошибка базы данных: {e}', 'error')
            
        return redirect(url_for('index'))

# --- СЕКРЕТНАЯ АДМИНКА (Обновлено для использования шаблона) ---
@app.route('/messages')
def view_messages():
    # Достаем все заявки из базы, новые (непрочитанные) сверху
    all_requests = ClientRequest.query.order_by(
        ClientRequest.is_read.asc(), # Сначала False (непрочитанные)
        ClientRequest.date.desc()    # Потом по дате (самые новые)
    ).all()
    
    # Передаем список заявок в шаблон messages.html
    return render_template('messages.html', requests=all_requests)

# --- НОВЫЙ РОУТ: Пометить заявку как прочитанную/непрочитанную ---
@app.route('/toggle_read/<int:request_id>', methods=['POST'])
def toggle_read(request_id):
    req = ClientRequest.query.get_or_404(request_id)
    
    try:
        # Инвертируем статус прочтения
        req.is_read = not req.is_read
        db.session.commit()
        
        status_text = 'прочитана' if req.is_read else 'непрочитана'
        flash(f'Заявка #{req.id} помечена как {status_text}.', 'info')
    except Exception as e:
        db.session.rollback()
        flash(f'Ошибка при обновлении статуса: {e}', 'error')
        
    # Возвращаемся на страницу со списком заявок
    return redirect(url_for('view_messages'))

# --- НОВЫЙ РОУТ: Удаление заявки ---
@app.route('/delete/<int:request_id>', methods=['POST'])
def delete_request(request_id):
    req = ClientRequest.query.get_or_404(request_id)
    
    try:
        db.session.delete(req)
        db.session.commit()
        flash(f'Заявка #{request_id} от {req.name} успешно удалена.', 'warning')
    except Exception as e:
        db.session.rollback()
        flash(f'Ошибка при удалении заявки: {e}', 'error')
    
    return redirect(url_for('view_messages'))


if __name__ == '__main__':
    # Добавлена проверка на существование базы данных
    if not os.path.exists('site.db'):
        with app.app_context():
            db.create_all()
    app.run(debug=True)