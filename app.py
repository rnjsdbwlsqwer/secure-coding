import sqlite3
import uuid
from flask import Flask, render_template, request, redirect, url_for, session, flash, g
from flask_socketio import SocketIO, send
from functools import wraps

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
DATABASE = 'market.db'
socketio = SocketIO(app)

# 데이터베이스 연결 관리: 요청마다 연결 생성 후 사용, 종료 시 close
def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row  # 결과를 dict처럼 사용하기 위함
    return db

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

# 테이블 생성 (최초 실행 시에만)
def init_db():
    with app.app_context():
        db = get_db()
        cursor = db.cursor()
        # 사용자 테이블 생성
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user (
                id TEXT PRIMARY KEY,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                bio TEXT
            )
        """)
        # 상품 테이블 생성
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS product (
        id TEXT PRIMARY KEY,
        title TEXT NOT NULL,
        description TEXT NOT NULL,
        price TEXT NOT NULL,
        category TEXT,
        views INTEGER DEFAULT 0,
        seller_id TEXT NOT NULL
            )
        """)
        # 신고 테이블 생성
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS report (
                id TEXT PRIMARY KEY,
                reporter_id TEXT NOT NULL,
                target_id TEXT NOT NULL,
                reason TEXT NOT NULL
            )
        """)
        
        # 계좌 테이블 생성 (잔액 저장)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS account (
                user_id TEXT PRIMARY KEY,
                balance REAL NOT NULL DEFAULT 0,
                FOREIGN KEY (user_id) REFERENCES user(id)
            )
        """)

        # 거래내역 테이블 생성
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS transactions (
                id TEXT PRIMARY KEY,
                sender_id TEXT NOT NULL,
                receiver_id TEXT NOT NULL,
                amount REAL NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (sender_id) REFERENCES user(id),
                FOREIGN KEY (receiver_id) REFERENCES user(id)
            )
        """)
        
        

        db.commit()

# 기본 라우트
@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return render_template('index.html')

# 회원가입
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        db = get_db()
        cursor = db.cursor()
        # 중복 사용자 체크
        cursor.execute("SELECT * FROM user WHERE username = ?", (username,))
        if cursor.fetchone() is not None:
            flash('이미 존재하는 사용자명입니다.')
            return redirect(url_for('register'))
        user_id = str(uuid.uuid4())
        cursor.execute("INSERT INTO user (id, username, password) VALUES (?, ?, ?)",
                       (user_id, username, password))
        db.commit()
        flash('회원가입이 완료되었습니다. 로그인 해주세요.')
        return redirect(url_for('login'))
    return render_template('register.html')

# 로그인
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        db = get_db()
        cursor = db.cursor()
        cursor.execute("SELECT * FROM user WHERE username = ? AND password = ?", (username, password))
        user = cursor.fetchone()
        if user:
            session['user_id'] = user['id']
            flash('로그인 성공!')
            return redirect(url_for('dashboard'))
        else:
            flash('아이디 또는 비밀번호가 올바르지 않습니다.')
            return redirect(url_for('login'))
    return render_template('login.html')

# 로그아웃
@app.route('/logout')
def logout():
    session.pop('user_id', None)
    flash('로그아웃되었습니다.')
    return redirect(url_for('index'))

# 대시보드
@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    db = get_db()
    cursor = db.cursor()
    
    # 현재 사용자 조회

    cursor.execute("SELECT * FROM user WHERE id = ?", (session['user_id'],))
    current_user = cursor.fetchone()


    # 상품 목록
    cursor.execute("SELECT * FROM product")
    all_products = cursor.fetchall()
    
    # 잔액 조회
    cursor.execute("SELECT balance FROM account WHERE user_id = ?", (session['user_id'],))
    account = cursor.fetchone()
    balance = account['balance'] if account else 0

    # 거래내역 조회
    cursor.execute("""
        SELECT t.id, u1.username AS sender, u2.username AS receiver, t.amount, t.timestamp
        FROM transactions t
        JOIN user u1 ON t.sender_id = u1.id
        JOIN user u2 ON t.receiver_id = u2.id
        WHERE t.sender_id = ? OR t.receiver_id = ?
        ORDER BY t.timestamp DESC
    """, (session['user_id'], session['user_id']))
    transaction_history = cursor.fetchall()

    # 다른 유저 목록 조회
    cursor.execute("SELECT username FROM user WHERE id != ?", (session['user_id'],))
    other_users = cursor.fetchall()

    # 모든 정보 함께 렌더링
    return render_template(
        'dashboard.html',
        products=all_products,
        user=current_user,
        balance=balance,
        transactions=transaction_history,
        other_users=other_users
    )



    # 거래 내역 조회 (송금한 내역과 받은 내역 모두 가져옴)
    cursor.execute("""
        SELECT t.id, u1.username AS sender, u2.username AS receiver, t.amount, t.timestamp
        FROM transactions t
        JOIN user u1 ON t.sender_id = u1.id
        JOIN user u2 ON t.receiver_id = u2.id
        WHERE t.sender_id = ? OR t.receiver_id = ?
        ORDER BY t.timestamp DESC
    """, (session['user_id'], session['user_id']))
    
    transaction_history = cursor.fetchall()

    return render_template(
        'dashboard.html',
        products=all_products,
        user=current_user,
        transactions=transaction_history  # 거래 내역을 템플릿에 전달
    )



    # 대시보드 함수 일부
    cursor.execute("SELECT username FROM user WHERE id != ?", (session['user_id'],))
    other_users = cursor.fetchall()

# 프로필 페이지: bio 업데이트 가능
@app.route('/profile', methods=['GET', 'POST'])
def profile():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    db = get_db()
    cursor = db.cursor()
    if request.method == 'POST':
        bio = request.form.get('bio', '')
        cursor.execute("UPDATE user SET bio = ? WHERE id = ?", (bio, session['user_id']))
        db.commit()
        flash('프로필이 업데이트되었습니다.')
        return redirect(url_for('profile'))
    cursor.execute("SELECT * FROM user WHERE id = ?", (session['user_id'],))
    current_user = cursor.fetchone()
    return render_template('profile.html', user=current_user)

# 상품 등록
@app.route('/product/new', methods=['GET', 'POST'])
def new_product():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        title = request.form['title']
        description = request.form['description']
        price = request.form['price']
        category = request.form['category']  # ✅ 이 부분 위치도 위로 올림

        db = get_db()
        cursor = db.cursor()
        product_id = str(uuid.uuid4())

        # ✅ 딱 한 번만 INSERT (category 포함해서)
        cursor.execute(
            "INSERT INTO product (id, title, description, price, category, seller_id) VALUES (?, ?, ?, ?, ?, ?)",
            (product_id, title, description, price, category, session['user_id'])
        )

        db.commit()
        flash('상품이 등록되었습니다.')
        return redirect(url_for('dashboard'))

    return render_template('new_product.html')


# 상품 상세보기
@app.route('/product/<product_id>')
def view_product(product_id):
    db = get_db()
    cursor = db.cursor()

    # 조회수 증가 먼저 수행
    cursor.execute("UPDATE product SET views = views + 1 WHERE id = ?", (product_id,))
    db.commit()

    # 상품 정보 가져오기
    cursor.execute("SELECT * FROM product WHERE id = ?", (product_id,))
    product = cursor.fetchone()

    if not product:
        flash('상품을 찾을 수 없습니다.')
        return redirect(url_for('dashboard'))

    # 판매자 정보
    cursor.execute("SELECT * FROM user WHERE id = ?", (product['seller_id'],))
    seller = cursor.fetchone()

    return render_template('view_product.html', product=product, seller=seller)

# 신고하기
@app.route('/report', methods=['GET', 'POST'])
def report():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    if request.method == 'POST':
        target_id = request.form['target_id']
        reason = request.form['reason']
        db = get_db()
        cursor = db.cursor()
        report_id = str(uuid.uuid4())
        cursor.execute(
            "INSERT INTO report (id, reporter_id, target_id, reason) VALUES (?, ?, ?, ?)",
            (report_id, session['user_id'], target_id, reason)
        )
        db.commit()
        flash('신고가 접수되었습니다.')
        return redirect(url_for('dashboard'))
    return render_template('report.html')

# 실시간 채팅: 클라이언트가 메시지를 보내면 전체 브로드캐스트
@socketio.on('send_message')
def handle_send_message_event(data):
    data['message_id'] = str(uuid.uuid4())
    send(data, broadcast=True)
 
 # 전체 채팅 페이지
@app.route('/chat')
def chat():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT username FROM user WHERE id = ?", (session['user_id'],))
    user = cursor.fetchone()
    return render_template('chat.html', username=user['username'])


# 1:1 채팅 페이지
@app.route('/chat/<target_username>')
def private_chat(target_username):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT username FROM user WHERE id = ?", (session['user_id'],))
    user = cursor.fetchone()
    return render_template('private_chat.html', username=user['username'], target_username=target_username)

# WebSocket: 1:1 채팅용 방 처리
from flask_socketio import join_room, leave_room, emit

@socketio.on('private_message')
def handle_private_message(data):
    room = get_private_room_name(data['sender'], data['receiver'])
    data['message_id'] = str(uuid.uuid4())
    emit('private_message', data, to=room)

@socketio.on('join_private_room')
def handle_join_private(data):
    room = get_private_room_name(data['sender'], data['receiver'])
    join_room(room)

@socketio.on('leave_private_room')
def handle_leave_private(data):
    room = get_private_room_name(data['sender'], data['receiver'])
    leave_room(room)

def get_private_room_name(user1, user2):
    return '-'.join(sorted([user1, user2]))

   
# 계좌 잔액 확인 기능    
@app.route('/balance')
def get_balance():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT balance FROM account WHERE user_id = ?", (session['user_id'],))
    account = cursor.fetchone()

    if not account:
        cursor.execute("INSERT INTO account (user_id, balance) VALUES (?, 0)", (session['user_id'],))
        db.commit()
        balance = 0
    else:
        balance = account['balance']
    
    return render_template('get_balance.html', balance=balance)


# 송금 기능
@app.route('/send_money', methods=['GET', 'POST'])
def send_money():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        receiver_username = request.form['receiver']
        amount = float(request.form['amount'])

        db = get_db()
        cursor = db.cursor()

        # 송금 대상 사용자 조회
        cursor.execute("SELECT id FROM user WHERE username = ?", (receiver_username,))
        receiver = cursor.fetchone()

        if not receiver:
            flash('해당 사용자명을 찾을 수 없습니다.')
            return redirect(url_for('send_money'))

        receiver_id = receiver['id']

        # 송금자 잔액 확인
        cursor.execute("SELECT balance FROM account WHERE user_id = ?", (session['user_id'],))
        sender_account = cursor.fetchone()

        if not sender_account or sender_account['balance'] < amount:
            flash('잔액이 부족합니다.')
            return redirect(url_for('send_money'))

        # 송금 처리 (트랜잭션 사용)
        try:
            cursor.execute("UPDATE account SET balance = balance - ? WHERE user_id = ?", (amount, session['user_id']))
            cursor.execute("UPDATE account SET balance = balance + ? WHERE user_id = ?", (amount, receiver_id))

            # 거래내역 저장
            transaction_id = str(uuid.uuid4())
            cursor.execute("""
                INSERT INTO transactions (id, sender_id, receiver_id, amount)
                VALUES (?, ?, ?, ?)
            """, (transaction_id, session['user_id'], receiver_id, amount))

            db.commit()
            flash(f'{receiver_username}님에게 {amount}원을 송금했습니다.')
        except Exception as e:
            db.rollback()
            flash('송금 중 오류가 발생했습니다.')

        return redirect(url_for('dashboard'))
    
    return render_template('send_money.html')

# 거래내역 조회 기능능
@app.route('/transactions')
def transaction_history():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    db = get_db()
    cursor = db.cursor()
    cursor.execute("""
        SELECT t.id, u1.username AS sender, u2.username AS receiver, t.amount, t.timestamp
        FROM transactions t
        JOIN user u1 ON t.sender_id = u1.id
        JOIN user u2 ON t.receiver_id = u2.id
        WHERE t.sender_id = ? OR t.receiver_id = ?
        ORDER BY t.timestamp DESC
    """, (session['user_id'], session['user_id']))

    transactions = cursor.fetchall()
    return render_template('transactions.html', transactions=transactions)


@app.route('/top_up', methods=['GET', 'POST'])
def top_up():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        amount = float(request.form['amount'])
        
        if amount <= 0:
            flash('충전 금액은 0보다 커야 합니다.')
            return redirect(url_for('top_up'))
        
        db = get_db()
        cursor = db.cursor()
        cursor.execute("UPDATE account SET balance = balance + ? WHERE user_id = ?", (amount, session['user_id']))
        db.commit()
        flash(f'{amount}원이 충전되었습니다.')
        return redirect(url_for('get_balance'))
    
    return render_template('top_up.html')

@app.route('/search')
def search():
    keyword = request.args.get('q', '')
    sort = request.args.get('sort', 'recent')
    category = request.args.get('category', '')

    db = get_db()
    cursor = db.cursor()
    query = "SELECT * FROM product WHERE title LIKE ?"
    params = [f"%{keyword}%"]

    if category:
        query += " AND category = ?"
        params.append(category)

    if sort == 'price':
        query += " ORDER BY CAST(price AS REAL) ASC"
    elif sort == 'popular':
        query += " ORDER BY views DESC"
    else:
        query += " ORDER BY ROWID DESC"

    cursor.execute(query, params)
    results = cursor.fetchall()

    return render_template('search_results.html', products=results, keyword=keyword)
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        db = get_db()
        cursor = db.cursor()
        cursor.execute("SELECT username FROM user WHERE id = ?", (session['user_id'],))
        user = cursor.fetchone()
        if user['username'] != 'admin':
            flash('관리자만 접근 가능합니다.')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/admin')
@admin_required
def admin_panel():
    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT * FROM user")
    users = cursor.fetchall()
    cursor.execute("SELECT * FROM product")
    products = cursor.fetchall()
    cursor.execute("""
        SELECT t.id, u1.username AS sender, u2.username AS receiver, t.amount, t.timestamp
        FROM transactions t
        JOIN user u1 ON t.sender_id = u1.id
        JOIN user u2 ON t.receiver_id = u2.id
        ORDER BY t.timestamp DESC
    """)
    transactions = cursor.fetchall()
    cursor.execute("SELECT * FROM report ORDER BY rowid DESC")
    reports = cursor.fetchall()
    return render_template('admin.html', users=users, products=products, transactions=transactions, reports=reports)

@app.route('/admin/delete_product/<product_id>', methods=['POST'])
@admin_required
def delete_product(product_id):
    db = get_db()
    cursor = db.cursor()
    cursor.execute("DELETE FROM product WHERE id = ?", (product_id,))
    db.commit()
    flash('상품이 삭제되었습니다.')
    return redirect(url_for('admin_panel'))

@app.route('/admin/deactivate_user/<user_id>', methods=['POST'])
@admin_required
def deactivate_user(user_id):
    db = get_db()
    cursor = db.cursor()
    cursor.execute("UPDATE user SET is_active = 0 WHERE id = ?", (user_id,))
    db.commit()
    flash('해당 유저를 휴면 처리했습니다.')
    return redirect(url_for('admin_panel'))



if __name__ == '__main__':
    init_db()  # 앱 컨텍스트 내에서 테이블 생성
    socketio.run(app, debug=True)  