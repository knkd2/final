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
                    item_id INTEGER NOT NULL,
                    status TEXT NOT NULL,
                    price REAL NOT NULL,
                    item_name TEXT NOT NULL,
                    acceptance_status TEXT DEFAULT '',
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
                    merchant_order_id INTEGER NOT NULL,
                    delivery_person_id INTEGER,
                    item_id INTEGER NOT NULL,
                    status TEXT NOT NULL,
                    price REAL NOT NULL,
                    item_name TEXT NOT NULL,
                    FOREIGN KEY (customer_id) REFERENCES users (id),
                    FOREIGN KEY (merchant_id) REFERENCES users (id),
                    FOREIGN KEY (delivery_person_id) REFERENCES users (id),
                    FOREIGN KEY (item_id) REFERENCES menu (id))''')
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
    # 獲取商家的訂單列表，包含外送員的狀態
    merchant_orders = conn.execute('''
        SELECT mo.*, 
               CASE WHEN do.status = '已接單' THEN '已接單' ELSE '未接單' END AS delivery_status
        FROM merchant_orders mo
        LEFT JOIN delivery_orders do ON mo.id = do.merchant_order_id
        WHERE mo.merchant_id = ?
    ''', (session['user_id'],)).fetchall()
    conn.close()

    return render_template('menu.html', menu_items=menu_items, merchant_orders=merchant_orders)
    


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
        # 更新訂單為已拒絕
        cursor.execute('UPDATE merchant_orders SET acceptance_status = "已拒絕" WHERE id = ?', (order_id,))
        cursor.execute('UPDATE orders SET acceptance_status = "已拒絕" WHERE id = ?', (order_id,))
        conn.commit()
        flash('訂單已拒絕。', 'success')
    except sqlite3.Error as e:
        flash(f'發生錯誤：{e}', 'danger')
        print(f'SQLite Error: {e}')  # 打印錯誤信息到控制台
        conn.rollback()
    finally:
        cursor.close()
        conn.close()

    return redirect(url_for('menu'))




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




@app.route('/view_reviews/<int:user_id>', methods=['GET'])
def view_reviews(user_id):
    if 'user_id' not in session:
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



# 顾客下单功能
@app.route('/place_order/<int:item_id>', methods=['POST'])
def place_order(item_id):
    if 'user_id' not in session or session['role'] != 'customer':
        return redirect(url_for('login'))

    conn = get_db_connection()

    # 获取菜品信息
    item = conn.execute('SELECT * FROM menu WHERE id = ?', (item_id,)).fetchone()

    # 获取价格和菜品名称
    price = item['price']
    item_name = item['item_name']

    # 创建订单
    conn.execute('''
        INSERT INTO orders (customer_id, merchant_id, item_id, item_name, price, status)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (session['user_id'], item['merchant_id'], item['id'], item_name, price, '待处理'))
    conn.commit()
    conn.close()



    flash('訂單已下單！', 'success')
    return redirect(url_for('orders'))  # 重定向到订单页面

@app.route('/delete_order/<int:order_id>', methods=['POST'])
def delete_order(order_id):
    if 'user_id' not in session or session['role'] != 'customer':
        return redirect(url_for('login'))

    conn = get_db_connection()
    order = conn.execute('SELECT status FROM orders WHERE id = ? AND customer_id = ?', (order_id, session['user_id'])).fetchone()

    if order:
        
        if order['status'] == '已確認':
            flash('已確認的訂單無法刪除', 'danger')
        else:
           
            conn.execute('DELETE FROM orders WHERE id = ? AND customer_id = ?', (order_id, session['user_id']))
            conn.commit()
            flash('訂單已刪除', 'success')
    else:
        
        flash('訂單未找到', 'danger')
    
    conn.close()
    return redirect(url_for('orders'))

@app.route('/confirm_order', methods=['POST'])
def confirm_order():
    if 'user_id' not in session or session['role'] != 'customer':
        return redirect(url_for('login'))

    conn = get_db_connection()
    cursor = conn.cursor()

    # 獲取選中的訂單 ID
    order_ids = request.form.getlist('order_ids')

    if not order_ids:
        flash('請選擇至少一個訂單進行確認！', 'warning')
        return redirect(url_for('orders'))

    # 將選中的訂單插入到商家訂單列表並更新狀態為“已確認”
    for order_id in order_ids:
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
            # 更新外送員的狀態為“已接單”
            cursor.execute(''' 
                UPDATE delivery_orders 
                SET delivery_person_id = ?, status = ? 
                WHERE id = ? 
            ''', (session['user_id'], '已接單', order_id))
            
            cursor.execute('''
                INSERT INTO merchant_orders (customer_id, merchant_id, item_id, status, delivery_status, price, item_name)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (order['customer_id'], order['merchant_id'], order['item_id'], '已確認', '待處理', order['price'], order['item_name']))
            
            cursor.execute('UPDATE orders SET status = "已確認" WHERE id = ?', (order['id'],))

    conn.commit()
    conn.close()

    flash('訂單已確認並通知商家！', 'success')
    return redirect(url_for('orders'))



@app.route('/orders', methods=['GET', 'POST'])
def orders():
    if 'user_id' not in session or session['role'] != 'customer':
        return redirect(url_for('login'))

    conn = get_db_connection()
    orders = conn.execute('''
        SELECT orders.id AS id,
               menu.item_name AS item_name,
               menu.price AS price,
               orders.status AS status,
               orders.acceptance_status AS acceptance_status,
               orders.merchant_id AS merchant_id,
               orders.delivery_person_id AS delivery_person_id
        FROM orders
        JOIN menu ON orders.item_id = menu.id
        WHERE orders.customer_id = ?
    ''', (session['user_id'],)).fetchall()

    # 只計算未確認的訂單金額
    total_price = sum(order['price'] for order in orders if order['status'] != '已確認')

    conn.close()
    return render_template('orders.html', orders=orders, total_price=total_price)






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
            flash('未找到訂單！', 'danger')
            return redirect(url_for('menu'))

        # 將訂單插入到外送訂單列表
        cursor.execute('''
            INSERT INTO delivery_orders (customer_id, merchant_id, delivery_person_id, item_id, status, price, item_name)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (order['customer_id'], order['merchant_id'], None, order['item_id'], '待配送', order['price'], order['item_name']))
       
        # 更新訂單為已通知外送員
        cursor.execute('UPDATE merchant_orders SET delivery_status = "已通知" WHERE id = ?', (order_id,))
        conn.commit()
        flash('订单已确认并发送给外送小哥！', 'success')
    except Exception as e:
        flash(f'發生錯誤：{e}', 'danger')
        conn.rollback()
    finally:
        cursor.close()
        conn.close()

    return redirect(url_for('menu'))







@app.route('/deliver_order/<int:order_id>', methods=['POST'])
def deliver_order(order_id):
    if 'user_id' not in session or session['role'] != 'delivery_person':
        return redirect(url_for('login'))

    conn = get_db_connection()
    cursor = conn.cursor()

    # 檢查訂單是否存在並且狀態是 "待配送"
    cursor.execute('SELECT status FROM delivery_orders WHERE id = ?', (order_id,))
    order = cursor.fetchone()

    if not order:
        flash('訂單不存在或已過期！', 'error')
        conn.close()
        return redirect(url_for('delivery_orders'))
    
    if order['status'] != '待配送':
        flash('該訂單目前無法接單，狀態為：' + order['status'], 'error')
        conn.close()
        return redirect(url_for('delivery_orders'))

    # 更新外送訂單的狀態和接單人
    cursor.execute('UPDATE delivery_orders SET delivery_person_id = ?, status = ? WHERE id = ?',
                (session['user_id'], '已接單', order_id))

    # 更新商家訂單的狀態為 "已接單"
    cursor.execute('UPDATE merchant_orders SET  delivery_status = ? WHERE id = ?',
                ( '已接單', order_id))

    conn.commit()
    conn.close()


    flash('訂單已成功接單！', 'success')
    return redirect(url_for('delivery_orders'))


@app.route('/accept_order/<int:order_id>', methods=['POST'])
def accept_order(order_id):
    if 'user_id' not in session or session['role'] != 'delivery_person':
        return redirect(url_for('login'))

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # 更新外送訂單為已接單
        cursor.execute('UPDATE delivery_orders SET status = "已接單", delivery_person_id = ? WHERE id = ?', (session['user_id'], order_id))
        conn.commit()
        flash('您已接單。', 'success')
    except Exception as e:
        flash(f'發生錯誤：{e}', 'danger')
        conn.rollback()
    finally:
        cursor.close()
        conn.close()

    return redirect(url_for('delivery_orders'))







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
        WHERE delivery_orders.status = '待配送' OR delivery_orders.status = '已接單'
    ''').fetchall()
    conn.close()

    return render_template('delivery_orders.html', delivery_orders=orders)

@app.route('/complete_order/<int:order_id>', methods=['POST'])
def complete_order(order_id):
    if 'user_id' not in session or session['role'] != 'customer':
        return redirect(url_for('login'))

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # 更新訂單狀態為已完成
        cursor.execute('UPDATE orders SET status = "已完成" WHERE id = ?', (order_id,))
        
        # 獲取訂單詳細信息
        order = cursor.execute('SELECT * FROM orders WHERE id = ?', (order_id,)).fetchone()
        
        # 記錄交易
        cursor.execute('''
            INSERT INTO transactions (user_id, amount, transaction_type)
            VALUES (?, ?, '支付')
        ''', (order['customer_id'], order['price']))

        # 更新商家報告
        cursor.execute('''
            INSERT INTO reports (user_id, report_type, total_received)
            VALUES (?, '商家', ?)
            ON CONFLICT(user_id, report_type) DO UPDATE SET
            total_received = total_received + excluded.total_received
        ''', (order['merchant_id'], order['price']))

        # 更新外送員報告
        if order['delivery_person_id']:
            cursor.execute('''
                INSERT INTO reports (user_id, report_type, total_orders)
                VALUES (?, '外送員', 1)
                ON CONFLICT(user_id, report_type) DO UPDATE SET
                total_orders = total_orders + 1
            ''', (order['delivery_person_id'],))

        # 更新客戶報告
        cursor.execute('''
            INSERT INTO reports (user_id, report_type, total_due)
            VALUES (?, '客戶', ?)
            ON CONFLICT(user_id, report_type) DO UPDATE SET
            total_due = total_due + excluded.total_due
        ''', (order['customer_id'], order['price']))

        conn.commit()
        flash('訂單已完成。', 'success')
    except sqlite3.Error as e:
        flash(f'發生錯誤：{e}', 'danger')
        print(f'SQLite Error: {e}')  # 打印錯誤信息到控制台
        conn.rollback()
    finally:
        cursor.close()
        conn.close()

    return redirect(url_for('menu'))



@app.route('/reports/<string:report_type>', methods=['GET'])
def view_reports(report_type):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    conn = get_db_connection()
    reports = conn.execute('''SELECT users.username, reports.total_received, reports.total_orders, reports.total_due
                              FROM reports
                              JOIN users ON reports.user_id = users.id
                              WHERE reports.report_type = ?''', (report_type,)).fetchall()
    conn.close()

    merchant_settlements = []
    delivery_settlements = []
    customer_settlements = []

    for report in reports:
        if report_type == '商家':
            merchant_settlements.append({'merchant_name': report['username'], 'amount': report['total_received']})
        elif report_type == '外送員':
            delivery_settlements.append({'delivery_name': report['username'], 'order_count': report['total_orders']})
        elif report_type == '客戶':
            customer_settlements.append({'customer_name': report['username'], 'amount': report['total_due']})

    return render_template('reports.html', 
                           merchant_settlements=merchant_settlements,
                           delivery_settlements=delivery_settlements,
                           customer_settlements=customer_settlements,
                           report_type=report_type)







"""import sqlite3  #刪除資料庫資料

def clear_orders():
    conn = sqlite3.connect('new_delivery.db')  # 請替換為你的資料庫名稱
    cursor = conn.cursor()

    # 刪除 orders 表中的所有資料
    cursor.execute('DELETE FROM "merchant_orders"')
    conn.commit()

    conn.close()
    print("已清空訂單表中的所有資料。")

# 執行清空訂單表操作
clear_orders()
"""

"""import sqlite3

# 連接到資料庫
conn = sqlite3.connect('new_delivery.db')  # 請將 'your_database_file.db' 替換為你的資料庫檔案名稱
cursor = conn.cursor()

# 刪除現有的 merchant_orders 資料表（如果存在）
cursor.execute("DROP TABLE IF EXISTS reviews")

# 重新創建 merchant_orders 資料表
cursor.execute('''CREATE TABLE IF NOT EXISTS reviews (
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

# 提交更改
conn.commit()

# 關閉資料庫連接
conn.close()

print("merchant_orders 資料表已刪除並重新建立")"""





if __name__ == '__main__':
    app.run(debug=True)
