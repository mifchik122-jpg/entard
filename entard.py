# entard.py - Соцсеть для проектов с загрузкой файлов
from flask import Flask, render_template_string, request, redirect, url_for, flash, session, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import os
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret-key-entard'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///entard.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB

# Создаем папки для загрузок
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

db = SQLAlchemy(app)

# Модели
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    projects = db.relationship('Project', backref='author', lazy=True)

class Project(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    repository_url = db.Column(db.String(500))
    languages = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    stars = db.Column(db.Integer, default=0)
    files_folder = db.Column(db.String(200))

class ProjectFile(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(200), nullable=False)
    filepath = db.Column(db.String(500), nullable=False)
    upload_date = db.Column(db.DateTime, default=datetime.utcnow)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=False)
    project = db.relationship('Project', backref='files')

# Создаем таблицы
with app.app_context():
    db.create_all()

# HTML шаблон
def render_page(title, content):
    auth_buttons = ""
    if 'user_id' in session:
        auth_buttons = f'''
        <a href="/create" class="btn btn-primary me-2">
            <i class="bi bi-plus-lg"></i> Новый проект
        </a>
        <a href="/profile" class="btn btn-outline-light me-2">
            <i class="bi bi-person-circle"></i> {session['username']}
        </a>
        <a href="/logout" class="btn btn-outline-danger">Выйти</a>
        '''
    else:
        auth_buttons = '''
        <a href="/login" class="btn btn-outline-light me-2">Войти</a>
        <a href="/register" class="btn btn-primary">Регистрация</a>
        '''
    
    base_html = f'''
    <!DOCTYPE html>
    <html lang="ru">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>{title} - Entard</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
        <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.8.1/font/bootstrap-icons.css">
        <style>
            body {{ background-color: #0d1117; color: #c9d1d9; }}
            .navbar {{ background-color: #161b22; border-bottom: 1px solid #30363d; }}
            .card {{ background-color: #161b22; border: 1px solid #30363d; }}
            .btn-primary {{ background-color: #238636; border-color: #238636; }}
            .btn-primary:hover {{ background-color: #2ea043; }}
            .language-bar {{ height: 8px; background: #30363d; border-radius: 4px; overflow: hidden; margin: 5px 0; }}
            .language-fill {{ height: 100%; float: left; }}
            .file-list {{ max-height: 300px; overflow-y: auto; }}
            .file-item {{ padding: 8px; border-bottom: 1px solid #30363d; }}
            .file-item:hover {{ background-color: #21262d; }}
        </style>
    </head>
    <body>
        <nav class="navbar navbar-expand-lg navbar-dark">
            <div class="container">
                <a class="navbar-brand" href="/">
                    <i class="bi bi-code-slash"></i> Entard
                </a>
                <div class="d-flex">
                    {auth_buttons}
                </div>
            </div>
        </nav>
        
        <div class="container mt-4">
            {content}
        </div>
        
        <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/js/bootstrap.bundle.min.js"></script>
    </body>
    </html>
    '''
    return base_html

# Главная страница
@app.route('/')
def index():
    projects = Project.query.order_by(Project.created_at.desc()).all()
    
    # Создаем HTML для проектов
    projects_html = ""
    for project in projects:
        langs_html = ""
        if project.languages:
            langs = project.languages.split(',')
            langs_html = '<div class="language-bar">'
            for lang in langs:
                if ':' in lang:
                    name, perc = lang.split(':')
                    color = f"hsl({hash(name) % 360}, 70%, 50%)"
                    langs_html += f'<div class="language-fill" style="width: {perc}%; background-color: {color};" title="{name}: {perc}%"></div>'
            langs_html += '</div>'
        
        projects_html += f'''
        <div class="col-md-4 mb-4">
            <div class="card h-100">
                <div class="card-body">
                    <h5 class="card-title">{project.title}</h5>
                    <p class="card-text text-muted">
                        {project.description[:100]}{"..." if len(project.description) > 100 else ""}
                    </p>
                    {langs_html}
                    <div class="d-flex justify-content-between align-items-center mt-3">
                        <small class="text-muted">
                            <i class="bi bi-person"></i> {project.author.username}
                        </small>
                        <small class="text-muted">
                            <i class="bi bi-star"></i> {project.stars}
                            <i class="bi bi-folder me-2 ms-2"></i> {len(project.files)}
                        </small>
                    </div>
                    <a href="/project/{project.id}" class="btn btn-sm btn-primary mt-2 w-100">Подробнее</a>
                </div>
            </div>
        </div>
        '''
    
    content = f'''
    <h1><i class="bi bi-code-slash"></i> Entard</h1>
    <p class="text-muted">Площадка для проектов с загрузкой файлов</p>
    
    <div class="row mt-4">
        {projects_html}
    </div>
    '''
    
    return render_page("Главная", content)

# Регистрация
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        
        if User.query.filter_by(username=username).first():
            flash('Имя пользователя уже занято')
            return redirect('/register')
        
        hashed_password = generate_password_hash(password)
        user = User(username=username, email=email, password_hash=hashed_password)
        
        db.session.add(user)
        db.session.commit()
        
        session['user_id'] = user.id
        session['username'] = user.username
        flash('Регистрация успешна!')
        return redirect('/')
    
    content = '''
    <div class="row justify-content-center">
        <div class="col-md-6">
            <div class="card">
                <div class="card-body">
                    <h2 class="text-center mb-4">Регистрация</h2>
                    
                    <form method="POST">
                        <div class="mb-3">
                            <label class="form-label">Имя пользователя</label>
                            <input type="text" name="username" class="form-control" required>
                        </div>
                        <div class="mb-3">
                            <label class="form-label">Email</label>
                            <input type="email" name="email" class="form-control" required>
                        </div>
                        <div class="mb-3">
                            <label class="form-label">Пароль</label>
                            <input type="password" name="password" class="form-control" required>
                        </div>
                        <button type="submit" class="btn btn-primary w-100">Зарегистрироваться</button>
                    </form>
                    
                    <div class="text-center mt-3">
                        <a href="/login">Уже есть аккаунт? Войти</a>
                    </div>
                </div>
            </div>
        </div>
    </div>
    '''
    
    return render_page("Регистрация", content)

# Вход
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        user = User.query.filter_by(username=username).first()
        
        if user and check_password_hash(user.password_hash, password):
            session['user_id'] = user.id
            session['username'] = user.username
            flash('Вход выполнен!')
            return redirect('/')
        else:
            flash('Неверные данные')
    
    content = '''
    <div class="row justify-content-center">
        <div class="col-md-6">
            <div class="card">
                <div class="card-body">
                    <h2 class="text-center mb-4">Вход</h2>
                    
                    <form method="POST">
                        <div class="mb-3">
                            <label class="form-label">Имя пользователя</label>
                            <input type="text" name="username" class="form-control" required>
                        </div>
                        <div class="mb-3">
                            <label class="form-label">Пароль</label>
                            <input type="password" name="password" class="form-control" required>
                        </div>
                        <button type="submit" class="btn btn-primary w-100">Войти</button>
                    </form>
                    
                    <div class="text-center mt-3">
                        <a href="/register">Нет аккаунта? Зарегистрироваться</a>
                    </div>
                </div>
            </div>
        </div>
    </div>
    '''
    
    return render_page("Вход", content)

# Выход
@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

# Создание проекта
@app.route('/create', methods=['GET', 'POST'])
def create_project():
    if 'user_id' not in session:
        return redirect('/login')
    
    if request.method == 'POST':
        title = request.form['title']
        description = request.form['description']
        repository_url = request.form['repository_url']
        languages = request.form['languages']
        
        # Создаем папку для файлов проекта
        import uuid
        folder_name = str(uuid.uuid4())[:8]
        project_folder = os.path.join(app.config['UPLOAD_FOLDER'], folder_name)
        os.makedirs(project_folder, exist_ok=True)
        
        project = Project(
            title=title,
            description=description,
            repository_url=repository_url,
            languages=languages,
            user_id=session['user_id'],
            files_folder=folder_name
        )
        
        db.session.add(project)
        db.session.commit()
        
        # Обработка загруженных файлов
        files = request.files.getlist('files')
        for file in files:
            if file and file.filename:
                filename = secure_filename(file.filename)
                filepath = os.path.join(project_folder, filename)
                file.save(filepath)
                
                project_file = ProjectFile(
                    filename=filename,
                    filepath=os.path.join(folder_name, filename),
                    project_id=project.id
                )
                db.session.add(project_file)
        
        db.session.commit()
        flash('Проект создан!')
        return redirect(f'/project/{project.id}')
    
    content = '''
    <div class="row justify-content-center">
        <div class="col-md-8">
            <div class="card">
                <div class="card-body">
                    <h2 class="mb-4">Создать проект</h2>
                    
                    <form method="POST" enctype="multipart/form-data">
                        <div class="mb-3">
                            <label class="form-label">Название проекта *</label>
                            <input type="text" name="title" class="form-control" required>
                        </div>
                        <div class="mb-3">
                            <label class="form-label">Описание *</label>
                            <textarea name="description" class="form-control" rows="3" required></textarea>
                        </div>
                        <div class="mb-3">
                            <label class="form-label">Ссылка на репозиторий (GitHub/GitLab)</label>
                            <input type="url" name="repository_url" class="form-control">
                        </div>
                        <div class="mb-3">
                            <label class="form-label">Языки программирования *</label>
                            <input type="text" name="languages" class="form-control" required
                                   placeholder="Python:60, JavaScript:30, HTML:10">
                            <small class="text-muted">Формат: Язык:процент, Язык:процент (сумма = 100%)</small>
                        </div>
                        <div class="mb-3">
                            <label class="form-label">Файлы проекта</label>
                            <input type="file" name="files" class="form-control" multiple>
                            <small class="text-muted">Можно выбрать несколько файлов</small>
                        </div>
                        <div class="d-flex justify-content-between">
                            <a href="/" class="btn btn-outline-light">Отмена</a>
                            <button type="submit" class="btn btn-primary">Создать проект</button>
                        </div>
                    </form>
                </div>
            </div>
        </div>
    </div>
    '''
    
    return render_page("Создать проект", content)

# Страница проекта
@app.route('/project/<int:project_id>')
def project_detail(project_id):
    project = Project.query.get_or_404(project_id)
    
    # Создаем HTML для языков
    langs_html = ""
    if project.languages:
        langs = project.languages.split(',')
        total_width = 0
        for lang in langs:
            if ':' in lang:
                name, perc = lang.split(':')
                color = f"hsl({hash(name) % 360}, 70%, 50%)"
                langs_html += f'''
                <div class="col-6 mb-2">
                    <div class="d-flex justify-content-between">
                        <span>{name}</span>
                        <span>{perc}%</span>
                    </div>
                    <div class="language-bar">
                        <div class="language-fill" style="width: {perc}%; background-color: {color};"></div>
                    </div>
                </div>
                '''
    
    # Создаем HTML для файлов
    files_html = ""
    for file in project.files:
        files_html += f'''
        <div class="file-item">
            <div class="d-flex justify-content-between align-items-center">
                <div>
                    <i class="bi bi-file-earmark"></i>
                    <span class="ms-2">{file.filename}</span>
                </div>
                <div>
                    <small class="text-muted me-3">{file.upload_date.strftime('%d.%m.%Y')}</small>
                    <a href="/download/{file.id}" class="btn btn-sm btn-outline-light">
                        <i class="bi bi-download"></i>
                    </a>
                </div>
            </div>
        </div>
        '''
    
    # Кнопки управления
    manage_buttons = ""
    if 'user_id' in session and session['user_id'] == project.user_id:
        manage_buttons = f'''
        <div class="mt-3">
            <button type="button" class="btn btn-outline-warning" data-bs-toggle="modal" data-bs-target="#addFilesModal">
                <i class="bi bi-plus-circle"></i> Добавить файлы
            </button>
        </div>
        '''
    
    content = f'''
    <div class="row">
        <div class="col-md-8">
            <div class="card mb-4">
                <div class="card-body">
                    <h1>{project.title}</h1>
                    <p class="lead">{project.description}</p>
                    
                    <div class="d-flex align-items-center mb-3">
                        <i class="bi bi-person-circle me-2"></i>
                        <strong>{project.author.username}</strong>
                        <span class="text-muted ms-3">
                            <i class="bi bi-calendar me-1"></i>
                            {project.created_at.strftime('%d.%m.%Y')}
                        </span>
                        <span class="text-muted ms-3">
                            <i class="bi bi-star me-1"></i>
                            {project.stars} звёзд
                        </span>
                    </div>
                    
                    {manage_buttons}
                </div>
            </div>
            
            <div class="card mb-4">
                <div class="card-body">
                    <h4><i class="bi bi-files"></i> Файлы проекта</h4>
                    {files_html if files_html else '<p class="text-muted">Файлов пока нет</p>'}
                </div>
            </div>
        </div>
        
        <div class="col-md-4">
            <div class="card mb-4">
                <div class="card-body">
                    <h4><i class="bi bi-code-slash"></i> Языки</h4>
                    <div class="row">
                        {langs_html if langs_html else '<p class="text-muted">Языки не указаны</p>'}
                    </div>
                </div>
            </div>
            
            <div class="card">
                <div class="card-body">
                    <h4><i class="bi bi-link"></i> Ссылки</h4>
                    {f'<a href="{project.repository_url}" target="_blank" class="btn btn-outline-light w-100 mb-2"><i class="bi bi-github"></i> Репозиторий</a>' if project.repository_url else ''}
                    <button class="btn btn-primary w-100" onclick="starProject({project.id})">
                        <i class="bi bi-star"></i> Поставить звезду
                    </button>
                </div>
            </div>
        </div>
    </div>
    
    <!-- Модальное окно для добавления файлов -->
    <div class="modal fade" id="addFilesModal" tabindex="-1">
        <div class="modal-dialog">
            <div class="modal-content">
                <div class="modal-header">
                    <h5 class="modal-title">Добавить файлы</h5>
                    <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                </div>
                <form action="/project/{project.id}/upload" method="POST" enctype="multipart/form-data">
                    <div class="modal-body">
                        <input type="file" name="files" class="form-control" multiple required>
                        <small class="text-muted">Можно выбрать несколько файлов</small>
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Отмена</button>
                        <button type="submit" class="btn btn-primary">Загрузить</button>
                    </div>
                </form>
            </div>
        </div>
    </div>
    
    <script>
    function starProject(projectId) {{
        fetch(`/project/${{projectId}}/star`, {{ method: 'POST' }})
            .then(response => response.json())
            .then(data => {{
                if (data.success) {{
                    alert('Звезда добавлена!');
                    location.reload();
                }}
            }});
    }}
    </script>
    '''
    
    return render_page(project.title, content)

# Загрузка файлов в проект
@app.route('/project/<int:project_id>/upload', methods=['POST'])
def upload_files(project_id):
    if 'user_id' not in session:
        return redirect('/login')
    
    project = Project.query.get_or_404(project_id)
    
    # Проверяем права
    if project.user_id != session['user_id']:
        flash('Нет прав на загрузку файлов')
        return redirect(f'/project/{project_id}')
    
    files = request.files.getlist('files')
    for file in files:
        if file and file.filename:
            filename = secure_filename(file.filename)
            project_folder = os.path.join(app.config['UPLOAD_FOLDER'], project.files_folder)
            filepath = os.path.join(project_folder, filename)
            file.save(filepath)
            
            project_file = ProjectFile(
                filename=filename,
                filepath=os.path.join(project.files_folder, filename),
                project_id=project.id
            )
            db.session.add(project_file)
    
    db.session.commit()
    flash('Файлы загружены!')
    return redirect(f'/project/{project_id}')

# Скачивание файла
@app.route('/download/<int:file_id>')
def download_file(file_id):
    file_record = ProjectFile.query.get_or_404(file_id)
    return send_from_directory(
        directory=app.config['UPLOAD_FOLDER'],
        path=file_record.filepath,
        as_attachment=True
    )

# Добавление звезды проекту
@app.route('/project/<int:project_id>/star', methods=['POST'])
def star_project(project_id):
    project = Project.query.get_or_404(project_id)
    project.stars += 1
    db.session.commit()
    return {'success': True}

# Профиль пользователя
@app.route('/profile')
def profile():
    if 'user_id' not in session:
        return redirect('/login')
    
    user = User.query.get(session['user_id'])
    projects = Project.query.filter_by(user_id=user.id).all()
    
    projects_html = ""
    for project in projects:
        projects_html += f'''
        <div class="card mb-3">
            <div class="card-body">
                <h5>{project.title}</h5>
                <p class="text-muted">{project.description[:100]}...</p>
                <div class="d-flex justify-content-between">
                    <small><i class="bi bi-star"></i> {project.stars} звёзд</small>
                    <small><i class="bi bi-folder"></i> {len(project.files)} файлов</small>
                    <small>{project.created_at.strftime('%d.%m.%Y')}</small>
                </div>
                <a href="/project/{project.id}" class="btn btn-sm btn-primary mt-2">Подробнее</a>
            </div>
        </div>
        '''
    
    content = f'''
    <div class="row">
        <div class="col-md-4">
            <div class="card">
                <div class="card-body text-center">
                    <h3><i class="bi bi-person-circle"></i></h3>
                    <h4>{user.username}</h4>
                    <p class="text-muted">{user.email}</p>
                    <div class="stats-box p-3">
                        <h5>{len(projects)}</h5>
                        <p class="text-muted">Проектов</p>
                    </div>
                    <p class="text-muted mt-3">На Entard с {user.created_at.strftime('%d.%m.%Y')}</p>
                </div>
            </div>
        </div>
        
        <div class="col-md-8">
            <h3>Мои проекты</h3>
            {projects_html if projects_html else '<div class="alert alert-info">У вас пока нет проектов</div>'}
            <a href="/create" class="btn btn-primary mt-3">
                <i class="bi bi-plus-lg"></i> Создать новый проект
            </a>
        </div>
    </div>
    '''
    
    return render_page(f"Профиль {user.username}", content)

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
