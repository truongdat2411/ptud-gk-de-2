from flask import Flask, render_template, redirect, url_for, request, flash, send_from_directory, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from models import db, User, Task, Category
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime, timezone, timedelta
import os
import uuid
import random
import requests
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
import numpy as np

# Định nghĩa các màu mặc định cho category
DEFAULT_COLORS = [
    "#4caf50", "#2196f3", "#f44336", "#ff9800", "#9c27b0", 
    "#3f51b5", "#e91e63", "#009688", "#673ab7", "#ffc107"
]

app = Flask(__name__)
app.config.from_object('config.Config')
db.init_app(app)
login_manager = LoginManager(app)

# Hàm helper để điều chỉnh múi giờ
def adjust_timezone(dt):
    if dt is None:
        return None
    # Nếu dt không có múi giờ, giả định nó là UTC
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    # Chuyển đổi sang múi giờ Việt Nam (UTC+7)
    vietnam_tz = timezone(timedelta(hours=7))
    return dt.astimezone(vietnam_tz)

# Hàm helper để định dạng thời gian
def format_datetime(dt, format='%d/%m/%Y %H:%M'):
    if dt is None:
        return ''
    return dt.strftime(format)

# Đăng ký các hàm helper với Jinja2
app.jinja_env.filters['adjust_timezone'] = adjust_timezone
app.jinja_env.filters['strftime'] = format_datetime

# Cấu hình upload file
UPLOAD_FOLDER = os.path.join(app.root_path, 'static', 'uploads', 'avatars')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Tạo tài khoản admin cố định nếu chưa tồn tại
def create_admin_account():
    with app.app_context():
        print("Đang kiểm tra tài khoản admin...")
        admin = User.query.filter_by(username='admin').first()
        if not admin:
            print("Không tìm thấy tài khoản admin, đang tạo mới...")
            hashed_password = generate_password_hash('admin123')
            
            # Tạo avatar mặc định
            try:
                # Đảm bảo thư mục tồn tại
                os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
                
                # Tạo tên file an toàn với UUID để tránh trùng lặp
                unique_filename = f"admin_{uuid.uuid4().hex}.png"
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
                
                # Tạo một ảnh đơn giản với màu nền
                color = (
                    random.randint(100, 255),
                    random.randint(100, 255),
                    random.randint(100, 255)
                )
                img = Image.new('RGB', (200, 200), color=color)
                img.save(file_path)
                
                # Tạo admin với avatar
                admin = User(username='admin', password=hashed_password, role='admin', avatar=unique_filename)
            except Exception as e:
                print(f"Lỗi khi tạo avatar cho admin: {e}")
                # Nếu có lỗi, tạo admin không có avatar
                admin = User(username='admin', password=hashed_password, role='admin')
            
            db.session.add(admin)
            db.session.commit()
            print("Đã tạo tài khoản admin mặc định")
        else:
            # Nếu tài khoản admin tồn tại nhưng không có quyền admin, cập nhật quyền
            if admin.role != 'admin':
                print(f"Tài khoản admin đã tồn tại nhưng không có quyền admin, đang cập nhật...")
                admin.role = 'admin'
                db.session.commit()
                print(f"Đã cập nhật tài khoản {admin.username} thành admin")
            else:
                print(f"Đã tìm thấy tài khoản admin: {admin.username}, role: {admin.role}")
                
                # Kiểm tra và cập nhật avatar nếu chưa có
                if not admin.avatar:
                    try:
                        # Đảm bảo thư mục tồn tại
                        os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
                        
                        # Tạo tên file an toàn với UUID để tránh trùng lặp
                        unique_filename = f"admin_{uuid.uuid4().hex}.png"
                        file_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
                        
                        # Tạo một ảnh đơn giản với màu nền
                        color = (
                            random.randint(100, 255),
                            random.randint(100, 255),
                            random.randint(100, 255)
                        )
                        img = Image.new('RGB', (200, 200), color=color)
                        img.save(file_path)
                        
                        # Cập nhật avatar cho admin
                        admin.avatar = unique_filename
                        db.session.commit()
                        print(f"Đã cập nhật avatar cho tài khoản admin")
                    except Exception as e:
                        print(f"Lỗi khi cập nhật avatar cho admin: {e}")

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        user = User.query.filter_by(username=username).first()
        
        if user and check_password_hash(user.password, password):
            # Kiểm tra xem tài khoản có bị khóa không
            if user.is_blocked:
                return render_template('index.html', error="Tài khoản của bạn đã bị khóa!")
            
            login_user(user)
            
            # Nếu là admin, chuyển hướng đến trang quản lý admin
            if user.role == 'admin':
                return redirect(url_for('admin_dashboard'))
            
            # Nếu là user thông thường, chuyển hướng đến dashboard
            return redirect(url_for('dashboard'))
        else:
            return render_template('index.html', error="Tên đăng nhập hoặc mật khẩu không đúng!")
    
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        role = 'user'  # Đặt mặc định là user
        
        # Kiểm tra xem username đã tồn tại chưa
        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            return render_template('register.html', error="Tên đăng nhập đã tồn tại!")
        
        # Tạo user mới
        hashed_password = generate_password_hash(password)
        
        # Tạo avatar mặc định
        try:
            # Đảm bảo thư mục tồn tại
            os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
            
            # Tạo tên file an toàn với UUID để tránh trùng lặp
            unique_filename = f"{uuid.uuid4().hex}.png"
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
            
            # Tạo một ảnh đơn giản với màu nền
            color = (
                random.randint(100, 255),
                random.randint(100, 255),
                random.randint(100, 255)
            )
            img = Image.new('RGB', (200, 200), color=color)
            img.save(file_path)
            
            # Tạo user với avatar
            user = User(username=username, password=hashed_password, role=role, avatar=unique_filename)
        except Exception as e:
            print(f"Lỗi khi tạo avatar: {e}")
            # Nếu có lỗi, tạo user không có avatar
            user = User(username=username, password=hashed_password, role=role)
        
        db.session.add(user)
        db.session.commit()
        
        # Đăng nhập người dùng sau khi đăng ký
        login_user(user)
        return redirect(url_for('dashboard'))
    
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        print(f"Đang xử lý đăng nhập cho user: {username}")
        user = User.query.filter_by(username=username).first()
        
        if user:
            print(f"Tìm thấy user: {user.username}, role: {user.role}")
            if check_password_hash(user.password, password):
                print("Mật khẩu chính xác")
                # Kiểm tra xem tài khoản có bị khóa không
                if user.is_blocked:
                    print("Tài khoản bị khóa")
                    return render_template('index.html', error="Tài khoản của bạn đã bị khóa!")
                
                login_user(user)
                print("Đăng nhập thành công")
                
                # Nếu là admin, chuyển hướng đến trang quản lý admin
                if user.role == 'admin':
                    print("Chuyển hướng đến trang admin")
                    return redirect(url_for('admin_dashboard'))
                
                # Nếu là user thông thường, chuyển hướng đến dashboard
                print("Chuyển hướng đến trang dashboard")
                return redirect(url_for('dashboard'))
            else:
                print("Mật khẩu không chính xác")
        else:
            print("Không tìm thấy user")
        
        return render_template('index.html', error="Tên đăng nhập hoặc mật khẩu không đúng!")
    
    # Chuyển hướng đến trang chủ thay vì hiển thị trang login riêng biệt
    return redirect(url_for('index'))

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

# Decorator để kiểm tra quyền admin
def admin_required(f):
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'admin':
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    decorated_function.__name__ = f.__name__
    return decorated_function

@app.route('/admin/dashboard')
@login_required
@admin_required
def admin_dashboard():
    # Lấy tất cả các task của admin và sắp xếp theo deadline
    tasks = Task.query.filter_by(user_id=current_user.id).order_by(
        Task.deadline.is_(None).asc(),
        Task.deadline.asc()
    ).all()
    
    # Lấy tất cả các category của admin
    categories = Category.query.filter_by(user_id=current_user.id).all()
    
    # Tính thời gian hiện tại
    now = datetime.now()
    
    return render_template('admin/dashboard.html', tasks=tasks, categories=categories, now=now)

@app.route('/admin/users')
@login_required
@admin_required
def admin_users():
    # Lấy tất cả các user không phải admin
    users = User.query.filter(User.role != 'admin').all()
    return render_template('admin/users.html', users=users)

@app.route('/admin/block_user/<int:user_id>')
@login_required
@admin_required
def admin_block_user(user_id):
    user = User.query.get_or_404(user_id)
    
    # Không cho phép khóa tài khoản admin
    if user.role == 'admin':
        flash('Không thể khóa tài khoản admin!', 'error')
        return redirect(url_for('admin_users'))
    
    user.is_blocked = True
    db.session.commit()
    flash(f'Đã khóa tài khoản {user.username}!', 'success')
    return redirect(url_for('admin_users'))

@app.route('/admin/unblock_user/<int:user_id>')
@login_required
@admin_required
def admin_unblock_user(user_id):
    user = User.query.get_or_404(user_id)
    user.is_blocked = False
    db.session.commit()
    flash(f'Đã mở khóa tài khoản {user.username}!', 'success')
    return redirect(url_for('admin_users'))

@app.route('/admin/delete_user/<int:user_id>')
@login_required
@admin_required
def admin_delete_user(user_id):
    user = User.query.get_or_404(user_id)
    
    # Không cho phép xóa tài khoản admin
    if user.role == 'admin':
        flash('Không thể xóa tài khoản admin!', 'error')
        return redirect(url_for('admin_users'))
    
    # Xóa tất cả các task của user
    Task.query.filter_by(user_id=user.id).delete()
    
    # Xóa tất cả các category của user
    Category.query.filter_by(user_id=user.id).delete()
    
    # Xóa user
    db.session.delete(user)
    db.session.commit()
    
    flash(f'Đã xóa tài khoản {user.username}!', 'success')
    return redirect(url_for('admin_users'))

@app.route('/dashboard')
@login_required
def dashboard():
    # Lấy tất cả các task của người dùng và sắp xếp theo deadline
    tasks = Task.query.filter_by(user_id=current_user.id).order_by(
        Task.deadline.is_(None).asc(),
        Task.deadline.asc()
    ).all()
    
    # Lấy tất cả các category của người dùng
    categories = Category.query.filter_by(user_id=current_user.id).all()
    
    # Tính thời gian hiện tại
    now = datetime.now()
    
    return render_template('dashboard.html', tasks=tasks, categories=categories, now=now)

@app.route('/add_task', methods=['POST'])
@login_required
def add_task():
    title = request.form['title']
    deadline_str = request.form.get('deadline')
    category_id = request.form.get('category_id')
    
    task = Task(title=title, user_id=current_user.id)
    
    # Thêm category nếu có
    if category_id and category_id.strip():
        category = Category.query.filter_by(id=category_id, user_id=current_user.id).first()
        if category:
            task.category_id = category.id
    
    if deadline_str and deadline_str.strip():
        try:
            # Chuyển đổi thời gian từ form thành UTC trước khi lưu vào database
            local_deadline = datetime.fromisoformat(deadline_str)
            # Thêm múi giờ Việt Nam vào thời gian local
            local_deadline = local_deadline.replace(tzinfo=timezone(timedelta(hours=7)))
            # Chuyển đổi sang UTC để lưu vào database
            utc_deadline = local_deadline.astimezone(timezone.utc)
            # Lưu thời gian không có thông tin múi giờ
            task.deadline = utc_deadline.replace(tzinfo=None)
        except ValueError:
            # Nếu định dạng không hợp lệ, bỏ qua
            pass
    
    db.session.add(task)
    db.session.commit()
    flash('Nhiệm vụ đã được thêm thành công!', 'success')
    # Chuyển hướng về trang dashboard tương ứng với role của người dùng
    if current_user.role == 'admin':
        return redirect(url_for('admin_dashboard'))
    return redirect(url_for('dashboard'))

@app.route('/complete_task/<int:task_id>')
@login_required
def complete_task(task_id):
    task = Task.query.get(task_id)
    if task and task.user_id == current_user.id:
        task.status = 'Completed'
        task.finished_at = db.func.current_timestamp()
        db.session.commit()
    # Chuyển hướng về trang dashboard tương ứng với role của người dùng
    if current_user.role == 'admin':
        return redirect(url_for('admin_dashboard'))
    return redirect(url_for('dashboard'))

@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    if request.method == 'POST':
        # Kiểm tra xem có yêu cầu tạo avatar ngẫu nhiên không
        if 'random_avatar' in request.form:
            try:
                # Đảm bảo thư mục tồn tại
                os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
                
                # Tạo tên file an toàn với UUID để tránh trùng lặp
                unique_filename = f"{uuid.uuid4().hex}.png"
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
                
                # Tạo một ảnh đơn giản với màu nền
                color = (
                    random.randint(100, 255),
                    random.randint(100, 255),
                    random.randint(100, 255)
                )
                img = Image.new('RGB', (200, 200), color=color)
                img.save(file_path)
                
                # Cập nhật avatar trong database
                current_user.avatar = unique_filename
                db.session.commit()
                
                flash('Avatar đã được cập nhật thành công!', 'success')
                return redirect(url_for('profile'))
            except Exception as e:
                flash(f'Lỗi khi tạo avatar: {str(e)}', 'error')
        # Kiểm tra xem có file được tải lên không
        elif 'avatar' in request.files:
            file = request.files['avatar']
            
            # Nếu người dùng không chọn file
            if file.filename == '':
                return render_template('profile.html', user=current_user, error="Không có file nào được chọn")
            
            # Nếu file hợp lệ
            if file and allowed_file(file.filename):
                # Tạo tên file an toàn với UUID để tránh trùng lặp
                filename = secure_filename(file.filename)
                file_extension = filename.rsplit('.', 1)[1].lower()
                unique_filename = f"{uuid.uuid4().hex}.{file_extension}"
                
                # Lưu file
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
                file.save(file_path)
                
                # Cập nhật avatar trong database
                current_user.avatar = unique_filename
                db.session.commit()
                
                flash('Avatar đã được cập nhật thành công!', 'success')
                return redirect(url_for('profile'))
            else:
                return render_template('profile.html', user=current_user, error="Chỉ chấp nhận file ảnh (png, jpg, jpeg, gif)")
    
    return render_template('profile.html', user=current_user)

@app.route('/uploads/avatars/<filename>')
def uploaded_file(filename):
    # Kiểm tra xem file có tồn tại không
    if filename and os.path.exists(os.path.join(app.config['UPLOAD_FOLDER'], filename)):
        return send_from_directory(app.config['UPLOAD_FOLDER'], filename)
    
    # Nếu không có filename hoặc file không tồn tại, tạo avatar mặc định
    try:
        # Đảm bảo thư mục tồn tại
        os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
        
        # Tạo tên file an toàn với UUID để tránh trùng lặp
        unique_filename = f"default_{uuid.uuid4().hex}.png"
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
        
        # Tạo một ảnh đơn giản với màu nền
        from PIL import Image
        
        # Tạo ảnh với kích thước 200x200 và màu ngẫu nhiên
        color = (
            random.randint(100, 255),
            random.randint(100, 255),
            random.randint(100, 255)
        )
        img = Image.new('RGB', (200, 200), color=color)
        img.save(file_path)
        
        return send_from_directory(app.config['UPLOAD_FOLDER'], unique_filename)
    except Exception as e:
        print(f"Lỗi khi tạo avatar mặc định: {e}")
        
        # Nếu có lỗi, tạo một file ảnh đơn giản bằng cách ghi trực tiếp
        try:
            # Tạo một file PNG đơn giản với màu đỏ
            unique_filename = f"simple_{uuid.uuid4().hex}.png"
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
            
            # Tạo một file PNG đơn giản (1x1 pixel màu đỏ)
            with open(file_path, 'wb') as f:
                # Đây là dữ liệu của một file PNG 1x1 pixel màu đỏ
                png_data = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xfa\xcf\x00\x00\x02\x00\x01H\xaf\xa4\x71\x00\x00\x00\x00IEND\xaeB`\x82'
                f.write(png_data)
            
            return send_from_directory(app.config['UPLOAD_FOLDER'], unique_filename)
        except Exception as e:
            print(f"Lỗi khi tạo file PNG đơn giản: {e}")
            # Nếu vẫn có lỗi, trả về 404
            return '', 404

@app.route('/categories')
@login_required
def categories():
    categories = Category.query.filter_by(user_id=current_user.id).all()
    return render_template('categories.html', categories=categories)

@app.route('/add_category', methods=['POST'])
@login_required
def add_category():
    name = request.form['name']
    color = request.form['color']
    
    # Kiểm tra xem tên danh mục đã tồn tại chưa
    existing_category = Category.query.filter_by(name=name, user_id=current_user.id).first()
    if existing_category:
        flash("Tên danh mục đã tồn tại!", "error")
        return redirect(url_for('categories'))
    
    category = Category(name=name, color=color, user_id=current_user.id)
    db.session.add(category)
    db.session.commit()
    
    flash(f'Đã thêm danh mục "{name}" thành công!', 'success')
    return redirect(url_for('categories'))

@app.route('/edit_category/<int:category_id>', methods=['POST'])
@login_required
def edit_category(category_id):
    category = Category.query.filter_by(id=category_id, user_id=current_user.id).first_or_404()
    
    name = request.form['name']
    color = request.form['color']
    
    # Kiểm tra xem tên danh mục đã tồn tại chưa (trừ danh mục hiện tại)
    existing_category = Category.query.filter(
        Category.name == name,
        Category.user_id == current_user.id,
        Category.id != category_id
    ).first()
    
    if existing_category:
        flash("Tên danh mục đã tồn tại!", "error")
        return redirect(url_for('categories'))
    
    category.name = name
    category.color = color
    db.session.commit()
    
    flash(f'Đã cập nhật danh mục "{name}" thành công!', 'success')
    return redirect(url_for('categories'))

@app.route('/delete_category/<int:category_id>')
@login_required
def delete_category(category_id):
    category = Category.query.filter_by(id=category_id, user_id=current_user.id).first_or_404()
    
    category_name = category.name
    
    # Cập nhật các task thuộc danh mục này về null
    Task.query.filter_by(category_id=category.id).update({Task.category_id: None})
    
    db.session.delete(category)
    db.session.commit()
    
    flash(f'Đã xóa danh mục "{category_name}" thành công!', 'success')
    return redirect(url_for('categories'))

@app.route('/reset_admin_password')
def reset_admin_password():
    admin = User.query.filter_by(username='admin').first()
    if admin:
        admin.password = generate_password_hash('admin123')
        admin.role = 'admin'  # Đảm bảo tài khoản có quyền admin
        db.session.commit()
        return render_template('index.html', message="Đã đặt lại mật khẩu cho tài khoản admin thành 'admin123'")
    else:
        return render_template('index.html', error="Không tìm thấy tài khoản admin!")

@app.route('/edit_task/<int:task_id>', methods=['GET', 'POST'])
@login_required
def edit_task(task_id):
    task = Task.query.filter_by(id=task_id, user_id=current_user.id).first_or_404()
    
    # Lấy tất cả các category của người dùng
    categories = Category.query.filter_by(user_id=current_user.id).all()
    
    # Tính thời gian hiện tại
    now = datetime.now()
    
    if request.method == 'POST':
        title = request.form['title']
        deadline_str = request.form.get('deadline')
        category_id = request.form.get('category_id')
        
        task.title = title
        
        # Cập nhật category
        if category_id and category_id.strip():
            category = Category.query.filter_by(id=category_id, user_id=current_user.id).first()
            if category:
                task.category_id = category.id
        else:
            task.category_id = None
        
        if deadline_str and deadline_str.strip():
            try:
                # Chuyển đổi thời gian từ form thành UTC trước khi lưu vào database
                local_deadline = datetime.fromisoformat(deadline_str)
                # Thêm múi giờ Việt Nam vào thời gian local
                local_deadline = local_deadline.replace(tzinfo=timezone(timedelta(hours=7)))
                # Chuyển đổi sang UTC để lưu vào database
                utc_deadline = local_deadline.astimezone(timezone.utc)
                # Lưu thời gian không có thông tin múi giờ
                task.deadline = utc_deadline.replace(tzinfo=None)
            except ValueError:
                # Nếu định dạng không hợp lệ, bỏ qua
                pass
        else:
            task.deadline = None
        
        db.session.commit()
        flash('Nhiệm vụ đã được cập nhật thành công!', 'success')
        # Chuyển hướng về trang dashboard tương ứng với role của người dùng
        if current_user.role == 'admin':
            return redirect(url_for('admin_dashboard'))
        return redirect(url_for('dashboard'))
    
    return render_template('edit_task.html', task=task, categories=categories, now=now)

@app.route('/admin/update_avatar')
@login_required
@admin_required
def admin_update_avatar():
    try:
        # Đảm bảo thư mục tồn tại
        os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
        
        # Tạo tên file an toàn với UUID để tránh trùng lặp
        unique_filename = f"admin_{uuid.uuid4().hex}.png"
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
        
        # Tạo một ảnh đơn giản với màu nền
        color = (
            random.randint(100, 255),
            random.randint(100, 255),
            random.randint(100, 255)
        )
        img = Image.new('RGB', (200, 200), color=color)
        img.save(file_path)
        
        # Cập nhật avatar cho admin
        current_user.avatar = unique_filename
        db.session.commit()
        
        flash('Avatar đã được cập nhật thành công!', 'success')
    except Exception as e:
        flash(f'Lỗi khi cập nhật avatar: {str(e)}', 'error')
    
    return redirect(url_for('profile'))

@app.route('/change_password', methods=['POST'])
@login_required
def change_password():
    current_password = request.form['current_password']
    new_password = request.form['new_password']
    confirm_password = request.form['confirm_password']
    
    # Kiểm tra mật khẩu hiện tại
    if not check_password_hash(current_user.password, current_password):
        flash('Mật khẩu hiện tại không đúng!', 'error')
        return redirect(url_for('profile'))
    
    # Kiểm tra mật khẩu mới và xác nhận mật khẩu
    if new_password != confirm_password:
        flash('Mật khẩu mới và xác nhận mật khẩu không khớp!', 'error')
        return redirect(url_for('profile'))
    
    # Kiểm tra độ dài mật khẩu mới
    if len(new_password) < 6:
        flash('Mật khẩu mới phải có ít nhất 6 ký tự!', 'error')
        return redirect(url_for('profile'))
    
    # Cập nhật mật khẩu mới
    current_user.password = generate_password_hash(new_password)
    db.session.commit()
    
    flash('Mật khẩu đã được cập nhật thành công!', 'success')
    return redirect(url_for('profile'))
