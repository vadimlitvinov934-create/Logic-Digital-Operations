import os
import logging
from datetime import datetime
from logging.handlers import RotatingFileHandler

from flask import Flask, render_template, request, flash, redirect, url_for, send_from_directory, abort
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, TextAreaField, SubmitField, BooleanField, SelectField
from wtforms.validators import DataRequired, Length, Email, EqualTo
from werkzeug.security import generate_password_hash, check_password_hash

# --- КОНФИГУРАЦИЯ ---
app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'ldo_super_secret_key_change_me_in_prod')

basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'site.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Инициализация расширений
db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Пожалуйста, войдите для доступа к этой странице.'
login_manager.login_message_category = 'info'

# --- ЛОГИРОВАНИЕ ---
if not app.debug:
    if not os.path.exists('logs'):
        os.mkdir('logs')
    file_handler = RotatingFileHandler('logs/ldo_site.log', maxBytes=10240, backupCount=10)
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'))
    file_handler.setLevel(logging.INFO)
    app.logger.addHandler(file_handler)
    app.logger.setLevel(logging.INFO)
    app.logger.info('LDO Startup')

# --- МОДЕЛИ БАЗЫ ДАННЫХ ---

class User(UserMixin, db.Model):
    """Модель администратора/пользователя"""
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    is_admin = db.Column(db.Boolean, default=False)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
        
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class ClientRequest(db.Model):
    """Модель заявки клиента"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    contact = db.Column(db.String(100), nullable=False)
    message = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), default='new') # new, in_progress, done
    date = db.Column(db.DateTime, default=datetime.utcnow)
    is_read = db.Column(db.Boolean, default=False)
    notes = db.Column(db.Text, nullable=True) # Заметки админа

class BlogPost(db.Model):
    """Модель для блога новостей компании"""
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    slug = db.Column(db.String(200), unique=True, nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_published = db.Column(db.Boolean, default=True)
    author_id = db.Column(db.Integer, db.ForeignKey('user.id'))

# --- ФОРМЫ (WTForms) ---

class LoginForm(FlaskForm):
    username = StringField('Логин', validators=[DataRequired()])
    password = PasswordField('Пароль', validators=[DataRequired()])
    remember_me = BooleanField('Запомнить меня')
    submit = SubmitField('Войти')

class RequestForm(FlaskForm):
    name = StringField('Ваше имя', validators=[DataRequired(), Length(min=2, max=50)])
    contact = StringField('Телефон или Telegram', validators=[DataRequired(), Length(min=5, max=100)])
    message = TextAreaField('Описание задачи', validators=[DataRequired()])
    submit = SubmitField('Отправить заявку')

class BlogPostForm(FlaskForm):
    title = StringField('Заголовок', validators=[DataRequired()])
    slug = StringField('URL (slug)', validators=[DataRequired()])
    content = TextAreaField('Содержание статьи', validators=[DataRequired()])
    is_published = BooleanField('Опубликовать сразу')
    submit = SubmitField('Сохранить')

# --- ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ---

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.context_processor
def inject_now():
    return {'now': datetime.utcnow()}

# --- РОУТЫ: ПУБЛИЧНЫЕ ---

@app.route('/favicon.ico')
def favicon():
    return send_from_directory(os.path.join(app.root_path, 'static'),
                               'favicon.ico', mimetype='image/vnd.microsoft.icon')

@app.route('/', methods=['GET', 'POST'])
def index():
    form = RequestForm()
    # Получаем последние 3 новости
    news = BlogPost.query.filter_by(is_published=True).order_by(BlogPost.created_at.desc()).limit(3).all()
    
    if form.validate_on_submit():
        try:
            new_req = ClientRequest(
                name=form.name.data,
                contact=form.contact.data,
                message=form.message.data
            )
            db.session.add(new_req)
            db.session.commit()
            flash('Заявка принята! Менеджер свяжется с вами в течение 15 минут.', 'success')
            return redirect(url_for('index', _anchor='contact'))
        except Exception as e:
            db.session.rollback()
            app.logger.error(f"Error saving request: {e}")
            flash('Произошла ошибка базы данных. Попробуйте позже.', 'danger')

    return render_template('index.html', form=form, news=news)

@app.route('/demo')
def demo():
    return render_template('demo.html')

@app.route('/blog')
def blog():
    posts = BlogPost.query.filter_by(is_published=True).order_by(BlogPost.created_at.desc()).all()
    return render_template('blog_list.html', posts=posts) # (Нужно создать этот шаблон)

@app.route('/blog/<slug>')
def blog_detail(slug):
    post = BlogPost.query.filter_by(slug=slug).first_or_404()
    return render_template('blog_detail.html', post=post) # (Нужно создать этот шаблон)

# --- РОУТЫ: АДМИНИСТРАТИВНЫЕ ---

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('admin_dashboard'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user is None or not user.check_password(form.password.data):
            flash('Неверный логин или пароль', 'danger')
            return redirect(url_for('login'))
        login_user(user, remember=form.remember_me.data)
        next_page = request.args.get('next')
        if not next_page or not next_page.startswith('/'):
            next_page = url_for('admin_dashboard')
        return redirect(next_page)
    return render_template('login.html', form=form)

@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/admin')
@login_required
def admin_dashboard():
    # Статистика для дашборда
    total_reqs = ClientRequest.query.count()
    unread_reqs = ClientRequest.query.filter_by(is_read=False).count()
    reqs = ClientRequest.query.order_by(ClientRequest.is_read.asc(), ClientRequest.date.desc()).all()
    return render_template('dashboard.html', requests=reqs, total=total_reqs, unread=unread_reqs)

@app.route('/admin/request/<int:request_id>/toggle', methods=['POST'])
@login_required
def toggle_read(request_id):
    req = ClientRequest.query.get_or_404(request_id)
    req.is_read = not req.is_read
    db.session.commit()
    flash(f'Статус заявки #{req.id} изменен', 'info')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/request/<int:request_id>/delete', methods=['POST'])
@login_required
def delete_request(request_id):
    req = ClientRequest.query.get_or_404(request_id)
    db.session.delete(req)
    db.session.commit()
    flash('Заявка удалена', 'warning')
    return redirect(url_for('admin_dashboard'))

# --- ОБРАБОТЧИКИ ОШИБОК ---

@app.errorhandler(404)
def not_found_error(error):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return render_template('500.html'), 500

# --- ЗАПУСК ---
if __name__ == '__main__':
    with app.app_context():
        # Создаем БД и админа при первом запуске, если нет
        db.create_all()
        if not User.query.filter_by(username='admin').first():
            admin = User(username='admin', email='admin@ldo.com', is_admin=True)
            admin.set_password('admin123') # В продакшене используйте ENV
            db.session.add(admin)
            db.session.commit()
            print("Администратор создан: admin / admin123")
    
    app.run(debug=True)

# Этот файл был значительно расширен для поддержки:
# 1. Полноценной аутентификации (Flask-Login).
# 2. Валидации форм через классы (Flask-WTF).
# 3. Системы блога/новостей.
# 4. Логирования ошибок в файл.
# 5. Безопасного хеширования паролей.