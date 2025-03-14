# Thông tin cá nhân

### Họ và tên: Trương Công Đạt

### MSSV: 22685561

---

# Mô tả dự án

## Tổng quan

Ứng dụng Quản lý Nhiệm vụ là một nền tảng web được phát triển để giúp người dùng tổ chức và theo dõi các công việc hàng ngày một cách hiệu quả. Dự án được xây dựng bằng Flask framework, kết hợp với SQLAlchemy để quản lý cơ sở dữ liệu và Flask-Login để xử lý xác thực người dùng.

## Mục tiêu

- Tạo một nền tảng đơn giản, dễ sử dụng để quản lý công việc cá nhân
- Cung cấp khả năng phân loại nhiệm vụ theo danh mục
- Hỗ trợ sắp xếp nhiệm vụ theo thời hạn để người dùng dễ dàng ưu tiên công việc
- Xây dựng hệ thống quản lý người dùng với phân quyền admin

## Đối tượng người dùng

- Người dùng cá nhân muốn quản lý công việc hàng ngày
- Sinh viên theo dõi bài tập và thời hạn nộp bài
- Nhóm làm việc nhỏ cần phân chia và theo dõi nhiệm vụ

## Tính năng nổi bật

1. **Giao diện thân thiện**: Thiết kế card-based hiện đại, dễ sử dụng trên nhiều thiết bị
3. **Quản lý thời hạn**: Thiết lập và theo dõi deadline cho từng nhiệm vụ
4. **Lọc và sắp xếp**: Lọc nhiệm vụ theo danh mục, trạng thái và sắp xếp theo thời hạn
5. **Hệ thống tài khoản**: Đăng ký, đăng nhập và quản lý hồ sơ cá nhân
6. **Quản trị viên**: Trang quản lý riêng cho admin để quản lý người dùng
7. **Hiển thị số task quá hạn**

## Công nghệ sử dụng

- **Backend**: Python, Flask, SQLAlchemy, Flask-Login
- **Frontend**: HTML, CSS, JavaScript
- **Cơ sở dữ liệu**: SQLite
- **Xác thực**: Werkzeug Security

## Triển khai

Ứng dụng được thiết kế để dễ dàng triển khai trên máy cá nhân thông qua script cài đặt tự động, giúp người dùng không cần kiến thức chuyên sâu về lập trình vẫn có thể sử dụng.

---

# Hướng dẫn cài đặt


## Cài đặt

### Cách 1: Cài đặt thủ công
   ```
1. Tạo môi trường ảo:
   ```
   python -m virtualenv venv
   ```
2. Kích hoạt môi trường ảo:
   - Windows: `venv\Scripts\activate`
   - Linux/Mac: `source venv/bin/activate`
3. Cài đặt các gói cần thiết:
   ```
   pip install -r requirements.txt
   ```
4. Khởi động ứng dụng:
   ```
   python app.py
   ```
5. Mở trình duyệt web và truy cập địa chỉ: http://localhost:5000

## Sử dụng

1. Truy cập ứng dụng tại địa chỉ: http://localhost:5000
2. Đăng ký tài khoản mới hoặc đăng nhập với tài khoản có sẵn
3. Tài khoản admin mặc định:
   - Tên đăng nhập: admin
   - Mật khẩu: admin123

## Cấu trúc dự án

- `app.py`: File chính để khởi động ứng dụng
- `routes.py`: Định nghĩa các route của ứng dụng
- `models.py`: Định nghĩa các model dữ liệu
- `config.py`: Cấu hình ứng dụng
- `templates/`: Thư mục chứa các template HTML
- `static/`: Thư mục chứa các file tĩnh (CSS, JS, hình ảnh)

## Liên hệ

Nếu bạn có bất kỳ câu hỏi hoặc góp ý nào, vui lòng liên hệ qua email: example@example.com
