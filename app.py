from flask import Flask, render_template, request, flash, redirect, url_for

app = Flask(__name__)
# Секретный ключ нужен для работы flash-сообщений (обязательно поменяй на сложный набор символов на проде)
app.secret_key = 'ldo_secret_key_change_this'

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/contact', methods=['POST'])
def contact():
    # Здесь логика обработки формы
    name = request.form.get('name')
    email = request.form.get('email')
    message = request.form.get('message')
    
    # Имитация отправки (можно потом подключить реальную почту или базу данных)
    print(f"Новая заявка: {name}, {email}, {message}")
    
    flash('Сообщение отправлено! Мы свяжемся с вами.', 'success')
    return redirect(url_for('home') + '#contact')

if __name__ == '__main__':
    # debug=True только для локальной разработки!
    app.run(debug=True)