from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)
    role = db.Column(db.String(50), nullable=False)  # 'customer', 'merchant', 'delivery_person'

class Restaurant(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    address = db.Column(db.String(200), nullable=False)
    owner_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    owner = db.relationship('User', backref=db.backref('restaurants', lazy=True))

class MenuItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(200), nullable=False)
    price = db.Column(db.Float, nullable=False)
    restaurant_id = db.Column(db.Integer, db.ForeignKey('restaurant.id'), nullable=False)
    restaurant = db.relationship('Restaurant', backref=db.backref('menu_items', lazy=True))

class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    restaurant_id = db.Column(db.Integer, db.ForeignKey('restaurant.id'), nullable=False)
    item_id = db.Column(db.Integer, db.ForeignKey('menu_item.id'), nullable=False)
    item_name = db.Column(db.String(100), nullable=False)
    price = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(100), nullable=False)  # 'pending', 'in progress', 'delivered'
    acceptance_status = db.Column(db.String(100), nullable=False, default='待確認')  # '待確認', '已接受', '已拒絕'
    delivery_status = db.Column(db.String(100), nullable=False, default='待確認')  # 添加這一行
    user = db.relationship('User', backref=db.backref('orders', lazy=True))
    restaurant = db.relationship('Restaurant', backref=db.backref('orders', lazy=True))
    menu_item = db.relationship('MenuItem', backref=db.backref('orders', lazy=True))

class DeliveryOrder(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('order.id'), nullable=False)
    delivery_person_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    pickup_status = db.Column(db.String(100), nullable=False)  # '待取貨', '取貨中', '已取貨'
    delivery_status = db.Column(db.String(100), nullable=False)  # '待送達', '送達中', '已送達'
    order = db.relationship('Order', backref=db.backref('delivery_order', uselist=False))
    delivery_person = db.relationship('User', backref=db.backref('delivery_orders', lazy=True))

class Review(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('order.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    rating = db.Column(db.Integer, nullable=False)
    comment = db.Column(db.String(500), nullable=False)
    order = db.relationship('Order', backref=db.backref('reviews', lazy=True))
    user = db.relationship('User', backref=db.backref('reviews', lazy=True))

class Transaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    transaction_type = db.Column(db.String(100), nullable=False)  # 'order_completed', etc.
    user = db.relationship('User', backref=db.backref('transactions', lazy=True))

class Report(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    report_type = db.Column(db.String(100), nullable=False)  # 'merchant', 'delivery_person', 'customer'
    total_received = db.Column(db.Float, default=0)
    total_orders = db.Column(db.Integer, default=0)
    total_due = db.Column(db.Float, default=0)
    user = db.relationship('User', backref=db.backref('reports', lazy=True))

def init_db():
    db.create_all()


