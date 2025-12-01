from flask import Flask, render_template, request, flash, redirect, url_for
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'super_secret_key_ldo'

# Временная "База данных" в оперативной памяти
messages_db = []

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/contact', methods=['POST'])
def contact():
    name = request.form.get('name')
    email = request.form.get('email')
    category = request.form.get('category')
    message_text = request.form.get('message')
    
    # Сохраняем заявку
    new_message = {
        'id': len(messages_db) + 1,
        'name': name,
        'email': email,
        'category': category,
        'message': message_text,
        'time': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    messages_db.insert(0, new_message) # Добавляем в начало списка (новые сверху)
    
    flash('Спасибо! Ваша заявка принята. Мы свяжемся с вами в ближайшее время.', 'success')
    return redirect(url_for('home') + '#contact')

# Секретная админка
@app.route('/vadimadmin')
def admin_panel():
    # Простая аналитика: считаем сколько заявок от каждого email
    stats = {}
    for msg in messages_db:
        email = msg['email']
        stats[email] = stats.get(email, 0) + 1
    
    # Сортируем статистику (кто больше всех пишет - тот сверху)
    sorted_stats = sorted(stats.items(), key=lambda item: item[1], reverse=True)

    return render_template('admin.html', messages=messages_db, stats=sorted_stats, total=len(messages_db))

if __name__ == '__main__':
    app.run(debug=True)