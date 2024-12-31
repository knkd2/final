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
                    FOREIGN KEY (customer_id) REFERENCES users (id),
                    FOREIGN KEY (merchant_id) REFERENCES users (id),
                    FOREIGN KEY (delivery_person_id) REFERENCES users (id),
                    FOREIGN KEY (item_id) REFERENCES menu (id))''')

    # 創建店家的訂單表
    conn.execute('''CREATE TABLE IF NOT EXISTS merchant_orders (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    customer_id INTEGER NOT NULL,
                    merchant_id INTEGER NOT NULL,
                    item_id INTEGER NOT NULL,
                    status TEXT NOT NULL,
                    price REAL NOT NULL,
                    item_name TEXT NOT NULL,
                    FOREIGN KEY (customer_id) REFERENCES users (id),
                    FOREIGN KEY (merchant_id) REFERENCES users (id),
                    FOREIGN KEY (item_id) REFERENCES menu (id))''')

    # 創建外送訂單表
    conn.execute('''CREATE TABLE IF NOT EXISTS delivery_orders (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    customer_id INTEGER NOT NULL,
                    merchant_id INTEGER NOT NULL,
                    delivery_person_id INTEGER,
                    item_id INTEGER NOT NULL,
                    status TEXT NOT NULL,
                    price REAL NOT NULL,
                    item_name TEXT NOT NULL,
                    FOREIGN KEY (customer_id) REFERENCES users (id),
                    FOREIGN KEY (merchant_id) REFERENCES users (id),
                    FOREIGN KEY (delivery_person_id) REFERENCES users (id),
                    FOREIGN KEY (item_id) REFERENCES menu (id))''')


    # 添加交易明細表
    conn.execute('''CREATE TABLE IF NOT EXISTS transactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    amount REAL NOT NULL,
                    transaction_type TEXT NOT NULL,
                    FOREIGN KEY (user_id) REFERENCES users (id))''')

    # 添加報告表
    conn.execute('''CREATE TABLE IF NOT EXISTS reports (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    total_received REAL,
                    total_orders INTEGER,
                    total_due REAL,
                    report_type TEXT NOT NULL,
                    FOREIGN KEY (user_id) REFERENCES users (id))''')





    # 添加测试用户
    users = [
        ('merchant', generate_password_hash('merchant123'), 'merchant'),
        ('customer', generate_password_hash('customer123'), 'customer'),
        ('delivery', generate_password_hash('delivery123'), 'delivery_person')
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
        LEFT JOIN delivery_orders do ON mo.id = do.id
        WHERE mo.merchant_id = ?
    ''', (session['user_id'],)).fetchall()
    conn.close()

    return render_template('menu.html', menu_items=menu_items, merchant_orders=merchant_orders)



# 更新订单状态
@app.route('/update_order_status/<int:order_id>', methods=['POST'])
def update_order_status(order_id):
    if 'user_id' not in session or session['role'] != 'merchant':
        return redirect(url_for('login'))

    conn = get_db_connection()
    conn.execute('UPDATE orders SET status = "已确认" WHERE id = ?', (order_id,))
    conn.commit()
    conn.close()

    flash('訂單已確認！', 'success')
    return redirect(url_for('menu'))




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

    # 创建订单
    conn.execute('''
        INSERT INTO orders (customer_id, merchant_id, item_id, status)
        VALUES (?, ?, ?, ?)
    ''', (session['user_id'], item['merchant_id'], item['id'], '待处理'))
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
        print(f"Deleting order with ID {order_id}, current status: {order['status']}")  # 調試輸出
        if order['status'] == '已確認':
            flash('已確認的訂單無法刪除', 'danger')
        else:
            print(f"Deleting order from database with ID {order_id}")  # 調試輸出
            conn.execute('DELETE FROM orders WHERE id = ? AND customer_id = ?', (order_id, session['user_id']))
            conn.commit()
            flash('訂單已刪除', 'success')
    else:
        print(f"Order not found with ID {order_id}")  # 調試輸出
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
            cursor.execute('''
                INSERT INTO merchant_orders (customer_id, merchant_id, item_id, status, price, item_name)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (order['customer_id'], order['merchant_id'], order['item_id'], '已確認', order['price'], order['item_name']))
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
               orders.status AS status
        FROM orders
        JOIN menu ON orders.item_id = menu.id
        WHERE orders.customer_id = ?
    ''', (session['user_id'],)).fetchall()

    # 計算總金額
    total_price = sum(order['price'] for order in orders)

    conn.close()
    return render_template('orders.html', orders=orders, total_price=total_price)





@app.route('/confirm_for_delivery/<int:order_id>', methods=['POST'])
def confirm_for_delivery(order_id):
    if 'user_id' not in session or session['role'] != 'merchant':
        return redirect(url_for('login'))

    conn = get_db_connection()
    cursor = conn.cursor()

    # 獲取商家確認的訂單
    order = cursor.execute('SELECT * FROM merchant_orders WHERE id = ?', (order_id,)).fetchone()
    print(f"Order to be transferred: {order}")  # 調試輸出

    # 檢查訂單是否存在
    if order is None:
        flash('未找到訂單！', 'danger')
        return redirect(url_for('menu'))

    # 將訂單插入到外送訂單列表
    cursor.execute('''
        INSERT INTO delivery_orders (customer_id, merchant_id, delivery_person_id, item_id, status, price, item_name)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (order['customer_id'], order['merchant_id'], None, order['item_id'], '待配送', order['price'], order['item_name']))
    print(f"Inserted order {order['id']} into delivery_orders")  # 調試輸出

    conn.commit()
    conn.close()

    flash('订单已确认并发送给外送小哥！', 'success')
    return redirect(url_for('menu'))

@app.route('/deliver_order/<int:order_id>', methods=['POST'])
def deliver_order(order_id):
    if 'user_id' not in session or session['role'] != 'delivery_person':
        return redirect(url_for('login'))

    conn = get_db_connection()
    conn.execute('UPDATE delivery_orders SET delivery_person_id = ?, status = ? WHERE id = ?',
                 (session['user_id'], '已接單', order_id))
    conn.commit()
    conn.close()

    flash('订单已接单！', 'success')
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



@app.route('/delivery')
def delivery_dashboard():
    if 'user_id' not in session or session['role'] != 'delivery_person':
        return redirect(url_for('login'))

    # 配送员管理订单状态等信息
    conn = get_db_connection()
    orders = conn.execute('''
        SELECT delivery_orders.id AS id, 
               menu.item_name AS item_name, 
               delivery_orders.status AS status
        FROM delivery_orders
        JOIN menu ON delivery_orders.item_id = menu.id
        WHERE delivery_orders.delivery_person_id = ?
    ''', (session['user_id'],)).fetchall()
    conn.close()

    return render_template('delivery_orders.html', orders=orders)



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

@app.route('/settle_accounts', methods=['POST'])
def settle_accounts():
    conn = get_db_connection()
    cursor = conn.cursor()

    # 計算商家應收金額
    merchants = cursor.execute('''SELECT merchant_id, SUM(price) as total_received
                                  FROM merchant_orders
                                  WHERE status = "已完成"
                                  GROUP BY merchant_id''').fetchall()
    
    for merchant in merchants:
        cursor.execute('''INSERT INTO transactions (user_id, amount, transaction_type) 
                          VALUES (?, ?, ?)''', (merchant['merchant_id'], merchant['total_received'], '應收'))
        cursor.execute('''INSERT INTO reports (user_id, total_received, report_type) 
                          VALUES (?, ?, ?)''', (merchant['merchant_id'], merchant['total_received'], '商家'))
    
    # 計算外送員接單數
    delivery_persons = cursor.execute('''SELECT delivery_person_id, COUNT(*) as total_orders
                                         FROM orders
                                         WHERE delivery_person_id IS NOT NULL
                                         GROUP BY delivery_person_id''').fetchall()
    
    for person in delivery_persons:
        cursor.execute('''INSERT INTO reports (user_id, total_orders, report_type) 
                          VALUES (?, ?, ?)''', (person['delivery_person_id'], person['total_orders'], '外送員'))
    
    # 計算客戶應付金額
    customers = cursor.execute('''SELECT customer_id, SUM(price) as total_due
                                  FROM orders
                                  WHERE status = "已完成"
                                  GROUP BY customer_id''').fetchall()
    
    for customer in customers:
        cursor.execute('''INSERT INTO reports (user_id, total_due, report_type) 
                          VALUES (?, ?, ?)''', (customer['customer_id'], customer['total_due'], '客戶'))
    
    conn.commit()
    conn.close()
    flash('結算完成', 'success')
    return redirect(url_for('dashboard'))

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
    cursor.execute('DELETE FROM orders')
    conn.commit()

    conn.close()
    print("已清空訂單表中的所有資料。")

# 執行清空訂單表操作
clear_orders()"""



if __name__ == '__main__':
    app.run(debug=True)
