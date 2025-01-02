from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3

app = Flask(__name__, static_folder='static', static_url_path='/')
app.secret_key = '123TyU%^&'

# 数据库名称
DB_NAME = 'new_delivery.db'

# 数据库连接
def get_db_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()

    # 創建用戶表
    conn.execute('''CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    role TEXT NOT NULL)''')

    # 創建菜單表
    conn.execute('''CREATE TABLE IF NOT EXISTS menu (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    item_name TEXT NOT NULL,
                    description TEXT NOT NULL,
                    price REAL NOT NULL,
                    merchant_id INTEGER NOT NULL,
                    FOREIGN KEY (merchant_id) REFERENCES users (id))''')

    # 創建訂單表
    conn.execute('''CREATE TABLE IF NOT EXISTS orders (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    customer_id INTEGER NOT NULL,
                    merchant_id INTEGER NOT NULL,
                    delivery_person_id INTEGER,
                    delivery_status TEXT  DEFAULT '待確認',
                    item_id INTEGER NOT NULL,
                    status TEXT NOT NULL,
                    price REAL NOT NULL,
                    item_name TEXT NOT NULL,
                    acceptance_status TEXT DEFAULT '待確認',
                    FOREIGN KEY (customer_id) REFERENCES users (id),
                    FOREIGN KEY (merchant_id) REFERENCES users (id),
                    FOREIGN KEY (delivery_person_id) REFERENCES users (id),
                    FOREIGN KEY (item_id) REFERENCES menu (id))''')

    # 創建店家的訂單表
    conn.execute('''CREATE TABLE IF NOT EXISTS merchant_orders (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        order_id INTEGER,
                        customer_id INTEGER NOT NULL,
                        merchant_id INTEGER NOT NULL,
                        item_id INTEGER NOT NULL,
                        status TEXT NOT NULL,
                        delivery_person_id INTEGER,
                        delivery_status TEXT DEFAULT '未接單',
                        acceptance_status TEXT DEFAULT '未處理',
                        price REAL NOT NULL,
                        item_name TEXT NOT NULL,
                        FOREIGN KEY (customer_id) REFERENCES users (id),
                        FOREIGN KEY (merchant_id) REFERENCES users (id),
                        FOREIGN KEY (item_id) REFERENCES menu (id),
                        FOREIGN KEY (order_id) REFERENCES orders (id))''')

    # 創建外送訂單表
    conn.execute('''CREATE TABLE IF NOT EXISTS delivery_orders (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    customer_id INTEGER NOT NULL,
                    merchant_id INTEGER NOT NULL,
                    merchant_order_id INTEGER,
                    delivery_person_id INTEGER,
                    item_id INTEGER NOT NULL,
                    status TEXT NOT NULL,
                    price REAL NOT NULL,
                    item_name TEXT NOT NULL,
                    FOREIGN KEY (customer_id) REFERENCES users (id),
                    FOREIGN KEY (merchant_id) REFERENCES users (id),
                    FOREIGN KEY (delivery_person_id) REFERENCES users (id),
                    FOREIGN KEY (item_id) REFERENCES menu (id))''')
    
    conn.execute('''CREATE TABLE IF NOT EXISTS notifications(
                    notification_id INTEGER PRIMARY  KEY AUTOINCREMENT,
                    user_id INTEGRT,
                    message TEXT,
                    is_read BOOLEAN DEFAULT 0)''')

    conn.execute('''CREATE TABLE IF NOT EXISTS transactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    amount REAL NOT NULL,
                    transaction_type TEXT NOT NULL,
                    FOREIGN KEY (user_id) REFERENCES users (id))''')
     
    # 創建報告表 
    conn.execute('''CREATE TABLE IF NOT EXISTS reports (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    report_type TEXT NOT NULL,
                    total_received REAL DEFAULT 0,
                    total_orders INTEGER DEFAULT 0,
                    total_due REAL DEFAULT 0,
                    UNIQUE(user_id, report_type),
                    FOREIGN KEY (user_id) REFERENCES users(id))''')
    
    conn.execute('''CREATE TABLE IF NOT EXISTS reviews (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER NOT NULL,
                        reviewed_user_id INTEGER NOT NULL,
                        order_id INTEGER NOT NULL,
                        rating INTEGER NOT NULL,
                        comment TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (user_id) REFERENCES users (id),
                        FOREIGN KEY (reviewed_user_id) REFERENCES users (id),
                        FOREIGN KEY (order_id) REFERENCES orders (id))''')

    # 添加测试用户
    users = [
        ('merchant', generate_password_hash('merchant123'), 'merchant'),
        ('customer', generate_password_hash('customer123'), 'customer'),
        ('delivery', generate_password_hash('delivery123'), 'delivery_person'),
        ('settle', generate_password_hash('settle123'), 'settle')
    ]

    for user in users:
        try:
            conn.execute('INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)', user)
        except sqlite3.IntegrityError:
            pass

    conn.commit()
    conn.close()

# 初始化数据库
init_db()


# 登录功能
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password']

        conn = get_db_connection()
        user = conn.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
        conn.close()

        if user and check_password_hash(user['password_hash'], password):
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['role'] = user['role']
            
            # 根据角色重定向到不同页面
            if user['role'] == 'merchant':
                return redirect(url_for('menu'))  # 商家菜单管理页面
            elif user['role'] == 'customer':
                return redirect(url_for('index'))  # 顾客订单页面
            elif user['role'] == 'delivery_person':
                return redirect(url_for('delivery_orders'))  # 配送员的管理页面
            # 配送員管理頁面 
            elif user['role'] == 'settle': return redirect(url_for('view_reports', report_type='settle')) # 結算管理頁面
        else:
            flash('用户名或密码错误，请重试。', 'error')

    return render_template('login.html')


# 登出功能
@app.route('/logout', methods=['POST'])
def logout():
    session.clear()
    flash('您已成功登出。', 'success')
    return redirect(url_for('index'))

# 首页
@app.route('/', methods=['GET'])
def index():
    logged_in = 'user_id' in session  # 判断是否登录
    conn = get_db_connection()
    
    # 获取菜品列表
    menu_items = conn.execute('SELECT * FROM menu').fetchall()
    
    # 获取用户的订单信息（如果已登录）
    orders = []
    if logged_in:
        orders = conn.execute('''SELECT orders.id, menu.item_name, orders.status 
                                 FROM orders
                                 JOIN menu ON orders.item_id = menu.id
                                 WHERE orders.customer_id = ?''', (session['user_id'],)).fetchall()
    
    conn.close()

    return render_template('index.html', menu_items=menu_items, logged_in=logged_in, orders=orders)


@app.route('/menu', methods=['GET', 'POST'])
def menu():
    if 'user_id' not in session or session['role'] != 'merchant':
        return redirect(url_for('login'))

    conn = get_db_connection()

    if request.method == 'POST':
        item_name = request.form['item_name']
        description = request.form['description']
        price = float(request.form['price'])

        conn.execute(
            'INSERT INTO menu (item_name, description, price, merchant_id) VALUES (?, ?, ?, ?)',
            (item_name, description, price, session['user_id'])
        )
        conn.commit()
        flash('菜品添加成功！', 'success')
        return redirect(url_for('menu'))

    # 獲取商家的菜品列表
    menu_items = conn.execute('SELECT * FROM menu WHERE merchant_id = ?', (session['user_id'],)).fetchall()
    
    # 獲取商家的訂單列表，包含所有可能的訂單狀態
    merchant_orders = conn.execute('''
        SELECT mo.*, 
               CASE 
                   WHEN do.status = '已接單' THEN '已接單'
                   WHEN do.status = '已送達' THEN '已送達'
                   WHEN do.status = '取貨中' THEN '取貨中'
                   WHEN mo.status = '已完成' THEN '已完成'
                   ELSE '未接單' 
               END AS delivery_status
        FROM merchant_orders mo
        LEFT JOIN delivery_orders do ON mo.id = do.merchant_order_id
        WHERE mo.merchant_id = ?
    ''', (session['user_id'],)).fetchall()
    
    conn.close()

    return render_template('menu.html', menu_items=menu_items, merchant_orders=merchant_orders)


    
# 删除菜品
@app.route('/menu/delete/<int:item_id>', methods=['POST'])
def delete_item(item_id):
    if 'user_id' not in session or session['role'] != 'merchant':
        return redirect(url_for('login'))

    conn = get_db_connection()
    conn.execute('DELETE FROM menu WHERE id = ? AND merchant_id = ?', (item_id, session['user_id']))
    conn.commit()
    conn.close()

    flash('菜品已删除！', 'success')
    return redirect(url_for('menu'))



# 编辑菜品
@app.route('/menu/edit/<int:item_id>', methods=['GET', 'POST'])
def edit_item(item_id):
    if 'user_id' not in session or session['role'] != 'merchant':
        return redirect(url_for('login'))

    conn = get_db_connection()
    if request.method == 'POST':
        item_name = request.form['item_name']
        description = request.form['description']
        price = float(request.form['price'])

        conn.execute('UPDATE menu SET item_name = ?, description = ?, price = ? WHERE id = ? AND merchant_id = ?',(item_name, description, price, item_id, session['user_id']))
        conn.commit()
        conn.close()
        flash('菜品更新成功！', 'success')
        return redirect(url_for('menu'))

    menu_item = conn.execute('SELECT * FROM menu WHERE id = ? AND merchant_id = ?',(item_id, session['user_id'])).fetchone()
    conn.close()

    return render_template('edit_item.html', item=menu_item)



@app.route('/confirm_for_delivery/<int:order_id>', methods=['POST'])
def confirm_for_delivery(order_id):
    if 'user_id' not in session or session['role'] != 'merchant':
        return redirect(url_for('login'))

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # 獲取商家確認的訂單
        order = cursor.execute('SELECT * FROM merchant_orders WHERE id = ?', (order_id,)).fetchone()
        
        if order is None:
            print(f"No order found with id {order_id}")
            flash('未找到訂單！', 'danger')
            return redirect(url_for('menu'))


        # 將訂單插入到外送訂單列表
        print("Inserting into delivery_orders")
        cursor.execute('''
            INSERT INTO delivery_orders (customer_id, merchant_id, delivery_person_id, item_id, status, price, item_name)
            VALUES (?, ?, ?, ?, ?, ?,  ?)
        ''', (order['customer_id'], order['merchant_id'],  None, order['item_id'], '待配送', order['price'], order['item_name']))

        # 確認插入的資料
        inserted_order = cursor.execute('SELECT * FROM delivery_orders WHERE merchant_order_id = ?', (order_id,)).fetchone()
        print(f"Inserted order details: {inserted_order}")

        # 更新訂單為已通知外送員
        cursor.execute('UPDATE merchant_orders SET delivery_status = "已通知" WHERE id = ?', (order_id,))
        conn.commit()
        flash('订单已确认并发送给外送小哥！', 'success')
    except Exception as e:
        print(f'發生錯誤：{e}')
        flash(f'發生錯誤：{e}', 'danger')
        conn.rollback()
    finally:
        cursor.close()
        conn.close()

    return redirect(url_for('menu'))



@app.route('/merchant_accept_order/<int:order_id>', methods=['POST'])
def merchant_accept_order(order_id):
    if 'user_id' not in session or session['role'] != 'merchant':
        return redirect(url_for('login'))

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # 更新訂單為已接單
        cursor.execute('UPDATE merchant_orders SET acceptance_status = "已接單" WHERE id = ?', (order_id,))
        cursor.execute('UPDATE orders SET acceptance_status = "已接單" WHERE id = ?', (order_id,))
        conn.commit()
        flash('訂單已接收。', 'success')
    except sqlite3.Error as e:
        flash(f'發生錯誤：{e}', 'danger')
        print(f'SQLite Error: {e}')  # 打印錯誤信息到控制台
        conn.rollback()
    finally:
        cursor.close()
        conn.close()

    return redirect(url_for('menu'))






@app.route('/merchant_reject_order/<int:order_id>', methods=['POST'])
def merchant_reject_order(order_id):
    if 'user_id' not in session or session['role'] != 'merchant':
        return redirect(url_for('login'))

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        print(f"Updating order {order_id} status to '已拒絕'")

        cursor.execute('UPDATE merchant_orders SET acceptance_status = ? WHERE id = ?', ("已拒絕", order_id))
        cursor.execute('UPDATE orders SET acceptance_status = ? WHERE id = ?', ("已拒絕", order_id))

        print("merchant_orders update result:", cursor.rowcount)
        print("orders update result:", cursor.rowcount)

        conn.commit()
        flash('訂單已拒絕。', 'success')

    except sqlite3.Error as e:
        flash(f'發生錯誤：{e}', 'danger')
        print(f'SQLite Error: {e}')
        conn.rollback()
    finally:
        cursor.close()
        conn.close()

    return redirect(url_for('menu'))  # 重定向到訂單頁面



@app.route('/view_reviews/<int:user_id>', methods=['GET'])
def view_reviews(user_id):
    if 'user_id' not in session or session['role'] != 'merchant':
        return redirect(url_for('login'))

    conn = get_db_connection()
    cursor = conn.cursor()

    reviews = cursor.execute('''
        SELECT reviews.rating, reviews.comment, users.username, reviews.created_at
        FROM reviews
        JOIN users ON reviews.user_id = users.id
        WHERE reviews.reviewed_user_id = ?
    ''', (user_id,)).fetchall()

    cursor.close()
    conn.close()

    return render_template('view_reviews.html', reviews=reviews)




@app.route('/orders', methods=['GET'])
def orders():
    if 'user_id' not in session or session['role'] != 'customer':
        return redirect(url_for('login'))

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        print("Executing orders query...")
        orders = cursor.execute('''
            SELECT orders.id AS id,
                   menu.item_name AS item_name,
                   menu.price AS price,
                   orders.status AS status,
                   orders.merchant_id AS merchant_id,
                   orders.delivery_person_id AS delivery_person_id,
                   orders.delivery_status AS delivery_status,
                   merchant_orders.acceptance_status AS merchant_acceptance_status
            FROM orders
            JOIN menu ON orders.item_id = menu.id
            LEFT JOIN merchant_orders ON orders.id = merchant_orders.order_id
            WHERE orders.customer_id = ?
        ''', (session['user_id'],)).fetchall()

        # 調試輸出查詢結果
        for order in orders:
            print(order)

        # 只計算未確認的訂單金額
        total_price = sum(order['price'] for order in orders if order['status'] != '已確認')

        return render_template('orders.html', orders=orders, total_price=total_price)
    except sqlite3.Error as e:
        print(f'SQLite Error: {e}')
        flash(f'發生錯誤：{e}', 'danger')
    finally:
        cursor.close()
        conn.close()

    return render_template('orders.html', orders=[], total_price=0)




# 顾客下单功能
@app.route('/place_order/<int:item_id>', methods=['POST'])
def place_order(item_id):
    if 'user_id' not in session or session['role'] != 'customer':
        return redirect(url_for('login'))

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # 获取菜品信息
        item = cursor.execute('SELECT * FROM menu WHERE id = ?', (item_id,)).fetchone()

        # 确保获取到菜品信息
        if item is None:
            flash('菜品不存在！', 'danger')
            return redirect(url_for('menu'))

        # 获取价格和菜品名称
        price = item['price']
        item_name = item['item_name']

        # 创建订单
        cursor.execute('''
            INSERT INTO orders (customer_id, merchant_id, item_id, item_name, price, status)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (session['user_id'], item['merchant_id'], item['id'], item_name, price, '待处理'))

        conn.commit()
        flash('訂單已下單！', 'success')
    except sqlite3.Error as e:
        flash(f'SQLite Error: {e}', 'danger')
        print(f'SQLite Error: {e}')
        conn.rollback()
    finally:
        cursor.close()
        conn.close()

    return redirect(url_for('orders'))  # 重定向到订单页面






@app.route('/delete_order/<int:order_id>', methods=['POST'])
def delete_order(order_id):
    if 'user_id' not in session or session['role'] != 'customer':
        print("User not authenticated or not a customer")
        return redirect(url_for('login'))

    conn = get_db_connection()
    print(f"Executing orders query for order ID: {order_id}")

    # 確認該訂單是否屬於當前用戶
    order = conn.execute(
        'SELECT id, status FROM orders WHERE id = ? AND customer_id = ?',
        (order_id, session['user_id'])
    ).fetchone()

    print(f"Order query result: {order}")

    if order:
        print(f"Order found: {order}")

        # 查詢第一筆訂單
        first_order = conn.execute(
            'SELECT id FROM orders WHERE customer_id = ? ORDER BY id ASC LIMIT 1',
            (session['user_id'],)
        ).fetchone()

        if first_order:
            print(f"First order for user ID {session['user_id']}: {dict(first_order)}")

        # 嚴格比較第一筆訂單的 ID 和傳入的 order_id
        if first_order and first_order['id'] == order_id:
            conn.execute('DELETE FROM orders WHERE id = ? AND customer_id = ?', (order_id, session['user_id']))
            conn.commit()
            flash('第一筆訂單已刪除', 'success')

        elif order['status'] == '已確認':
            print(f"Order with ID {order_id} is confirmed and cannot be deleted")
            flash('已確認的訂單無法刪除', 'danger')
        else:
            conn.execute('DELETE FROM orders WHERE id = ? AND customer_id = ?', (order_id, session['user_id']))
            conn.commit()
            flash('訂單已刪除', 'success')

    else:
        print(f"Order with ID {order_id} not found for user ID {session['user_id']}")
        flash('訂單未找到', 'danger')

    conn.close()
    return redirect(url_for('orders'))



@app.route('/confirm_order', methods=['POST'])
def confirm_order():
    if 'user_id' not in session or session['role'] != 'customer':
        return redirect(url_for('login'))

    conn = get_db_connection()
    cursor = conn.cursor()

    order_ids = request.form.getlist('order_ids')

    if not order_ids:
        flash('請選擇至少一個訂單來確認下單！', 'warning')
        return redirect(url_for('orders'))

    try:
        for order_id in order_ids:
            # 獲取訂單信息
            order = cursor.execute('''
                SELECT orders.id AS id,
                       orders.customer_id AS customer_id,
                       orders.merchant_id AS merchant_id,
                       orders.item_id AS item_id,
                       menu.item_name AS item_name,
                       menu.price AS price,
                       orders.status AS status
                FROM orders
                JOIN menu ON orders.item_id = menu.id
                WHERE orders.id = ? AND orders.customer_id = ?
            ''', (order_id, session['user_id'])).fetchone()

            if order:
                # 插入訂單到 merchant_orders 表，使用相同的訂單 ID
                cursor.execute('''
                    INSERT INTO merchant_orders (order_id, customer_id, merchant_id, item_id, item_name, price, status, acceptance_status)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (order['id'], order['customer_id'], order['merchant_id'], order['item_id'], order['item_name'], order['price'], '已確認', '待處理'))
                
                # 更新 orders 表中訂單的狀態
                cursor.execute('UPDATE orders SET status = "已確認" WHERE id = ?', (order['id'],))

        conn.commit()
        flash('訂單已確認並通知商家！', 'success')
    except sqlite3.Error as e:
        flash(f'SQLite Error: {e}', 'danger')
        print(f'SQLite Error: {e}')
        conn.rollback()
    finally:
        cursor.close()
        conn.close()

    return redirect(url_for('orders'))




@app.route('/add_review/<int:order_id>', methods=['POST'])
def add_review(order_id):
    if 'user_id' not in session or session['role'] != 'customer':
        return redirect(url_for('login'))

    rating = request.form['rating']
    comment = request.form['comment']
    reviewed_user_id = request.form['reviewed_user_id']

    if not reviewed_user_id:
        flash('請選擇一個評論對象', 'danger')
        return redirect(url_for('orders'))

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # 插入評論
        cursor.execute('''
            INSERT INTO reviews (user_id, reviewed_user_id, order_id, rating, comment)
            VALUES (?, ?, ?, ?, ?)
        ''', (session['user_id'], reviewed_user_id, order_id, rating, comment))

        conn.commit()
        flash('評論已提交。', 'success')
    except sqlite3.Error as e:
        flash(f'發生錯誤：{e}', 'danger')
        print(f'SQLite Error: {e}')  # 打印錯誤信息到控制台
        conn.rollback()
    finally:
        cursor.close()
        conn.close()

    return redirect(url_for('orders'))



@app.route('/confirm_receipt/<int:order_id>', methods=['POST'])
def confirm_receipt(order_id):
    if 'user_id' not in session or session['role'] != 'customer':
        return redirect(url_for('login'))

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # 更新訂單狀態為已完成
        cursor.execute('UPDATE orders SET status = "已完成" WHERE id = ?', (order_id,))
        
        # 確認外送訂單存在並更新狀態為已送達
        order = cursor.execute('SELECT * FROM orders WHERE id = ?', (order_id,)).fetchone()
        delivery_order_id = order['delivery_person_id']  # 假設此欄位包含 delivery_order_id
        delivery_order = cursor.execute('SELECT * FROM delivery_orders WHERE id = ?', (delivery_order_id,)).fetchone()
        if delivery_order:
            print(f"Delivery order found: {delivery_order}")
            cursor.execute('UPDATE delivery_orders SET status = "已完成" WHERE id = ?', (order_id,))
        else:
            print(f"No delivery order found with id {delivery_order_id}")
            flash('未找到外送訂單。', 'danger')

        # 更新商家訂單狀態為已完成
        cursor.execute('UPDATE merchant_orders SET status = "已完成" WHERE order_id = ?', (order_id,))

        # 更新報告資料
        merchant_income = order['price'] * 0.8
        delivery_person_income = order['price'] * 0.2

        # 將訂單完成的紀錄插入到交易表中
        cursor.execute('''
            INSERT INTO transactions (user_id, amount, transaction_type)
            SELECT customer_id, price, 'order_completed'
            FROM orders WHERE id = ?
        ''', (order_id,))

        # 更新商家報告
        cursor.execute('''
            INSERT INTO reports (user_id, report_type, total_received)
            VALUES (?, '商家', ?)
            ON CONFLICT(user_id, report_type) DO UPDATE SET
            total_received = total_received + excluded.total_received
        ''', (order['merchant_id'], merchant_income))

        # 更新外送員報告
        if order['delivery_person_id']:
            cursor.execute('''
                INSERT INTO reports (user_id, report_type, total_orders, total_received)
                VALUES (?, '外送員', 1, ?)
                ON CONFLICT(user_id, report_type) DO UPDATE SET
                total_orders = total_orders + 1,
                total_received = total_received + excluded.total_received
            ''', (order['delivery_person_id'], delivery_person_income))

        # 更新客戶報告
        cursor.execute('''
            INSERT INTO reports (user_id, report_type, total_due)
            VALUES (?, '客戶', ?)
            ON CONFLICT(user_id, report_type) DO UPDATE SET
            total_due = total_due + excluded.total_due
        ''', (order['customer_id'], order['price']))

        conn.commit()
        flash('訂單已完成，感謝您的確認。', 'success')

    except Exception as e:
        flash(f'發生錯誤：{e}', 'danger')
        print(f'發生錯誤：{e}')  # 調試用的詳細錯誤訊息
        conn.rollback()
    finally:
        cursor.close()
        conn.close()

    return redirect(url_for('orders'))









@app.route('/delivery_orders', methods=['GET'])
def delivery_orders():
    if 'user_id' not in session or session['role'] != 'delivery_person':
        return redirect(url_for('login'))

    conn = get_db_connection()
    orders = conn.execute('''
        SELECT delivery_orders.id AS id,
               delivery_orders.customer_id AS customer_id,
               users.username AS customer_name,
               delivery_orders.item_name AS item_name,
               delivery_orders.price AS price,
               delivery_orders.status AS status
        FROM delivery_orders
        JOIN users ON delivery_orders.customer_id = users.id
        WHERE delivery_orders.status IN ('待配送', '已接單', '取貨中', '已送達', '已完成')
    ''').fetchall()
    conn.close()

    return render_template('delivery_orders.html', delivery_orders=orders)


@app.route('/deliver_order/<int:order_id>', methods=['POST'])
def deliver_order(order_id):
    if 'user_id' not in session or session['role'] != 'delivery_person':
        return redirect(url_for('login'))

    conn = get_db_connection()
    try:
        print(f"Updating order id: {order_id} with delivery_person_id: {session['user_id']}")

        # 更新訂單狀態為已接單
        conn.execute('UPDATE orders SET delivery_status = "已接單", delivery_person_id = ? WHERE id = ?', (session['user_id'], order_id))
        print("Updated orders table")

        conn.execute('UPDATE delivery_orders SET status = "已接單", delivery_person_id = ? WHERE id = ?', (session['user_id'], order_id))
        conn.execute('UPDATE merchant_orders SET delivery_status = "已接單" , delivery_person_id=? WHERE id = ?', (session['user_id'],order_id,))
        print("Updated delivery_orders table")
        
        conn.commit()
        flash('訂單已接單，請前往取貨', 'success')
    except Exception as e:
        flash(f'發生錯誤：{e}', 'danger')
        print(f'Error occurred: {e}')
        conn.rollback()
    finally:
        conn.close()

    return redirect(url_for('delivery_orders'))



@app.route('/pickup_order/<int:order_id>', methods=['POST'])
def pickup_order(order_id):
    if 'user_id' not in session or session['role'] != 'delivery_person':
        return redirect(url_for('login'))

    conn = get_db_connection()
    try:
        # 更新 orders 表中的 delivery_status
        conn.execute('UPDATE orders SET delivery_status = "取貨中" WHERE id = ?', (order_id,))
        
        # 更新 delivery_orders 表中的狀態
        conn.execute('UPDATE delivery_orders SET status = "取貨中" WHERE id = ?', (order_id,))
        conn.execute('UPDATE merchant_orders SET delivery_status = "取貨中" WHERE id = ?', (order_id,))
        
        conn.commit()
        flash('訂單取貨中，請前往送達', 'success')

        # 通知顧客訂單正在取貨
        customer_id = conn.execute('SELECT customer_id FROM delivery_orders WHERE id = ?', (order_id,)).fetchone()['customer_id']
        conn.execute('''
            INSERT INTO notifications (user_id, message)
            VALUES (?, ?)
        ''', (customer_id, f'您的訂單正在取貨中，即將送達。訂單編號：{order_id}'))
        conn.commit()
    except Exception as e:
        flash(f'發生錯誤：{e}', 'danger')
        conn.rollback()
    finally:
        conn.close()

    return redirect(url_for('delivery_orders'))


@app.route('/complete_delivery/<int:order_id>', methods=['POST'])
def complete_delivery(order_id):
    if 'user_id' not in session or session['role'] != 'delivery_person':
        return redirect(url_for('login'))

    conn = get_db_connection()
    try:
        # 更新訂單狀態為已送達
        conn.execute('UPDATE orders SET delivery_status = "已送達" WHERE id = ?', (order_id,))
        conn.execute('UPDATE delivery_orders SET status = "已送達" WHERE id = ?', (order_id,))
        conn.execute('UPDATE merchant_orders SET delivery_status = "已送達" WHERE id = ?', (order_id,))
        conn.commit()
        flash('訂單已送達，感謝您的辛勤工作', 'success')

        # 通知顧客訂單已送達
        customer_id = conn.execute('SELECT customer_id FROM delivery_orders WHERE id = ?', (order_id,)).fetchone()['customer_id']
        conn.execute('''
            INSERT INTO notifications (user_id, message)
            VALUES (?, ?)
        ''', (customer_id, f'您的訂單已送達，請確認收貨並進行評價。訂單編號：{order_id}'))
        conn.commit()
    except Exception as e:
        flash(f'發生錯誤：{e}', 'danger')
        conn.rollback()
    finally:
        conn.close()

    return redirect(url_for('delivery_orders'))



@app.route('/view_delivery_reviews/<int:user_id>', methods=['GET'])
def view_delivery_reviews(user_id):
    if 'user_id' not in session or session['role'] != 'delivery_person':
        return redirect(url_for('login'))

    conn = get_db_connection()
    cursor = conn.cursor()

    reviews = cursor.execute('''
        SELECT reviews.rating, reviews.comment, users.username, reviews.created_at
        FROM reviews
        JOIN users ON reviews.user_id = users.id
        WHERE reviews.reviewed_user_id = ?
    ''', (user_id,)).fetchall()

    cursor.close()
    conn.close()

    return render_template('re.html', reviews=reviews)




@app.route('/view_reports', methods=['GET'])
def view_reports():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    conn = get_db_connection()

    # 查詢商家報告
    merchant_reports = conn.execute('''
        SELECT users.username AS merchant_name, reports.total_received
        FROM reports
        JOIN users ON reports.user_id = users.id
        WHERE reports.report_type = '商家'
    ''').fetchall()

    # 查詢外送員報告
    delivery_reports = conn.execute('''
        SELECT users.username AS delivery_name, reports.total_orders, reports.total_received
        FROM reports
        JOIN users ON reports.user_id = users.id
        WHERE reports.report_type = '外送員'
    ''').fetchall()

    # 查詢客戶報告
    customer_reports = conn.execute('''
        SELECT users.username AS customer_name, reports.total_due
        FROM reports
        JOIN users ON reports.user_id = users.id
        WHERE reports.report_type = '客戶'
    ''').fetchall()

    conn.close()

    return render_template('reports.html',
                           merchant_reports=merchant_reports,
                           delivery_reports=delivery_reports,
                           customer_reports=customer_reports)




"""
import sqlite3

# 連接到資料庫
conn = sqlite3.connect('new_delivery.db')  # 請將 'your_database_file.db' 替換為你的資料庫檔案名稱
cursor = conn.cursor()

# 刪除現有的 merchant_orders 資料表（如果存在）
cursor.execute("DROP TABLE IF EXISTS reports")

# 重新創建 merchant_orders 資料表
cursor.execute('''CREATE TABLE IF NOT EXISTS reports (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    report_type TEXT NOT NULL,
                    total_received REAL DEFAULT 0,
                    total_orders INTEGER DEFAULT 0,
                    total_due REAL DEFAULT 0,
                    UNIQUE(user_id, report_type),
                    FOREIGN KEY (user_id) REFERENCES users(id))''')

# 提交更改
conn.commit()

# 關閉資料庫連接
conn.close()

print("merchant_orders 資料表已刪除並重新建立")"""


if __name__ == '__main__':
    app.run(debug=True)
    
    
