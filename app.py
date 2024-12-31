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

    # 创建用户表
    conn.execute('''CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    role TEXT NOT NULL)''')

    # 创建菜单表
    conn.execute('''CREATE TABLE IF NOT EXISTS menu (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    item_name TEXT NOT NULL,
                    description TEXT NOT NULL,
                    price REAL NOT NULL,
                    merchant_id INTEGER NOT NULL,
                    FOREIGN KEY (merchant_id) REFERENCES users (id))''')

    # 创建订单表
    # 创建订单表时，确保存在必要的外键关联
    conn.execute('''CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_id INTEGER NOT NULL,
                merchant_id INTEGER NOT NULL,
                delivery_person_id INTEGER,
                item_id INTEGER NOT NULL,
                status TEXT NOT NULL,
                FOREIGN KEY (customer_id) REFERENCES users (id),
                FOREIGN KEY (merchant_id) REFERENCES users (id),
                FOREIGN KEY (delivery_person_id) REFERENCES users (id),
                FOREIGN KEY (item_id) REFERENCES menu (id))''')


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
                return redirect(url_for('orders'))  # 顾客订单页面
            elif user['role'] == 'delivery_person':
                return redirect(url_for('delivery_dashboard'))  # 配送员的管理页面
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



# 商家菜单管理
@app.route('/menu', methods=['GET', 'POST'])
def menu():
    if 'user_id' not in session or session['role'] != 'merchant':
        return redirect(url_for('login'))

    conn = get_db_connection()

    if request.method == 'POST':
        # 从表单获取数据
        item_name = request.form['item_name']
        description = request.form['description']
        price = float(request.form['price'])

        # 插入新的菜品到数据库
        conn.execute(
            'INSERT INTO menu (item_name, description, price, merchant_id) VALUES (?, ?, ?, ?)',
            (item_name, description, price, session['user_id'])
        )
        conn.commit()
        flash('菜品添加成功！', 'success')
        return redirect(url_for('menu'))

    # 获取商家的菜品列表
    menu_items = conn.execute('SELECT * FROM menu WHERE merchant_id = ?', (session['user_id'],)).fetchall()
    conn.close()

    return render_template('menu.html', menu_items=menu_items)



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

    if not item:
        flash('菜品不存在！', 'error')
        return redirect(url_for('index'))

    # 创建订单
    conn.execute('''
        INSERT INTO orders (customer_id, merchant_id, item_id, status)
        VALUES (?, ?, ?, ?)
    ''', (session['user_id'], item['merchant_id'], item['id'], '待处理'))
    conn.commit()
    conn.close()

    flash('订单已下单！', 'success')
    return redirect(url_for('orders'))  # 重定向到订单页面





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

        conn.execute('UPDATE menu SET item_name = ?, description = ?, price = ? WHERE id = ? AND merchant_id = ?',
                     (item_name, description, price, item_id, session['user_id']))
        conn.commit()
        conn.close()

        flash('菜品更新成功！', 'success')
        return redirect(url_for('menu'))

    menu_item = conn.execute('SELECT * FROM menu WHERE id = ? AND merchant_id = ?',
                              (item_id, session['user_id'])).fetchone()
    conn.close()

    if not menu_item:
        flash('菜品不存在或无权限编辑！', 'error')
        return redirect(url_for('menu'))

    return render_template('edit_item.html', item=menu_item)


# 顾客订单页面
# 顾客订单页面
@app.route('/orders')
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
    conn.close()
    return render_template('orders.html', orders=orders)



# 配送员管理页面
@app.route('/delivery')
def delivery_dashboard():
    if 'user_id' not in session or session['role'] != 'delivery_person':
        return redirect(url_for('login'))

    # 配送员管理订单状态等信息
    conn = get_db_connection()
    orders = conn.execute('''SELECT orders.id, menu.item_name, orders.status 
                             FROM orders
                             JOIN menu ON orders.item_id = menu.id
                             WHERE orders.delivery_person_id = ?''', (session['user_id'],)).fetchall()
    conn.close()

    return render_template('delivery_dashboard.html', orders=orders)


if __name__ == '__main__':
    app.run(debug=True)
