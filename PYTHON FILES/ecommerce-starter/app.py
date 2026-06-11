import os
import sqlite3
import uuid
from datetime import datetime, timedelta
from flask import Flask, jsonify, g, request, render_template, session
from flask_cors import CORS
from flask_mail import Mail, Message

try:
    import stripe
except ImportError:
    stripe = None

app = Flask(__name__)
app.secret_key = 'replace-this-with-a-random-secret'
CORS(app)

# Email Configuration
app.config['MAIL_SERVER'] = os.environ.get('MAIL_SERVER', 'smtp.mailtrap.io')
app.config['MAIL_PORT'] = int(os.environ.get('MAIL_PORT', 465))
app.config['MAIL_USE_SSL'] = os.environ.get('MAIL_USE_SSL', True)
app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME', 'demo@isho-macarvelle.com')
app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD', 'demo-password')
app.config['MAIL_DEFAULT_SENDER'] = os.environ.get('MAIL_DEFAULT_SENDER', 'orders@isho-macarvelle.com')
mail = Mail(app)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE = os.path.join(BASE_DIR, 'data.db')
DB_INITIALIZED = False
ADMIN_SEED_KEY = os.environ.get('ADMIN_SEED_KEY', 'seedsecret')

# Stripe Configuration
STRIPE_SECRET_KEY = os.environ.get('STRIPE_SECRET_KEY', 'sk_test_placeholder_key_DO_NOT_USE_IN_PRODUCTION')
STRIPE_PUBLISHABLE_KEY = os.environ.get('STRIPE_PUBLISHABLE_KEY', 'pk_test_placeholder_key_DO_NOT_USE_IN_PRODUCTION')
if stripe:
    stripe.api_key = STRIPE_SECRET_KEY

PRODUCTS = [
    {
        'id': 1,
        'name': 'Wireless Headphones',
        'description': 'Noise-cancelling over-ear headphones with long battery life.',
        'price': 100.00,
        'inventory': 24,
        'category': 'Audio',
        'image': 'https://via.placeholder.com/300x200.png?text=Headphones',
    },
    {
        'id': 2,
        'name': 'Smart Speaker',
        'description': 'Voice assistant speaker with rich sound and smart home control.',
        'price': 49.99,
        'inventory': 18,
        'category': 'Smart Home',
        'image': 'https://via.placeholder.com/300x200.png?text=Smart+Speaker',
    },
    {
        'id': 3,
        'name': 'Fitness Tracker',
        'description': 'Lightweight fitness tracker with heart-rate monitoring.',
        'price': 29.99,
        'inventory': 32,
        'category': 'Fitness',
        'image': 'https://via.placeholder.com/300x200.png?text=Fitness+Tracker',
    },
    {
        'id': 4,
        'name': 'Sneakers',
        'description': 'Comfortable sneakers for everyday wear.',
        'price': 250.00,
        'inventory': 52,
        'category': 'Footwear',
        'image': 'https://via.placeholder.com/300x200.png?text=Sneakers',
    },
]

def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(DATABASE, detect_types=sqlite3.PARSE_DECLTYPES)
        g.db.row_factory = sqlite3.Row
    return g.db


def close_db(e=None):
    db = g.pop('db', None)
    if db is not None:
        db.close()


@app.teardown_appcontext
def teardown_db(exception):
    close_db(exception)


def query_db(query, args=(), one=False):
    cur = get_db().execute(query, args)
    rv = cur.fetchall()
    cur.close()
    return (rv[0] if rv else None) if one else rv


def seed_products():
    if query_db('SELECT 1 FROM products LIMIT 1', one=True):
        return
    db = get_db()
    for product in PRODUCTS:
        db.execute(
            'INSERT OR IGNORE INTO products (id, name, description, price, inventory, category, image) VALUES (?, ?, ?, ?, ?, ?, ?)',
            (product['id'], product['name'], product['description'], product['price'], product['inventory'], product['category'], product['image'])
        )
    db.commit()


def seed_shipping_rates():
    if query_db('SELECT 1 FROM shipping_rates LIMIT 1', one=True):
        return
    db = get_db()
    # Flat rate for all countries
    db.execute('INSERT INTO shipping_rates (rate_type, country, cost) VALUES (?, ?, ?)', ('flat', None, 9.99))
    # Zone-based rates (examples)
    db.execute('INSERT INTO shipping_rates (rate_type, country, cost) VALUES (?, ?, ?)', ('zone', 'United States', 9.99))
    db.execute('INSERT INTO shipping_rates (rate_type, country, cost) VALUES (?, ?, ?)', ('zone', 'Canada', 15.99))
    db.execute('INSERT INTO shipping_rates (rate_type, country, cost) VALUES (?, ?, ?)', ('zone', 'United Kingdom', 12.99))
    db.execute('INSERT INTO shipping_rates (rate_type, country, cost) VALUES (?, ?, ?)', ('zone', 'Australia', 24.99))
    db.execute('INSERT INTO shipping_rates (rate_type, country, cost) VALUES (?, ?, ?)', ('zone', 'Other', 19.99))
    db.commit()


def seed_coupons():
    if query_db('SELECT 1 FROM coupons LIMIT 1', one=True):
        return
    db = get_db()
    # Sample coupons
    expiry = (datetime.now() + timedelta(days=30)).isoformat()
    db.execute(
        'INSERT INTO coupons (code, discount_type, discount_value, max_uses, expiry_date, active) VALUES (?, ?, ?, ?, ?, ?)',
        ('WELCOME10', 'percentage', 10, 100, expiry, 1)
    )
    db.execute(
        'INSERT INTO coupons (code, discount_type, discount_value, max_uses, expiry_date, active) VALUES (?, ?, ?, ?, ?, ?)',
        ('SAVE5', 'fixed', 5, 50, expiry, 1)
    )
    db.execute(
        'INSERT INTO coupons (code, discount_type, discount_value, max_uses, expiry_date, active) VALUES (?, ?, ?, ?, ?, ?)',
        ('SUMMER20', 'percentage', 20, 200, expiry, 1)
    )
    db.commit()


def init_db():
    with app.app_context():
        db = get_db()
        db.execute('''
            CREATE TABLE IF NOT EXISTS users (
                email TEXT PRIMARY KEY,
                password TEXT NOT NULL,
                name TEXT NOT NULL
            )
        ''')
        db.execute('''
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT NOT NULL,
                price REAL NOT NULL,
                inventory INTEGER NOT NULL,
                category TEXT,
                image TEXT
            )
        ''')
        db.execute('''
            CREATE TABLE IF NOT EXISTS reviews (
                id TEXT PRIMARY KEY,
                product_id INTEGER NOT NULL,
                user_email TEXT NOT NULL,
                user_name TEXT NOT NULL,
                rating INTEGER NOT NULL,
                comment TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY(user_email) REFERENCES users(email),
                FOREIGN KEY(product_id) REFERENCES products(id)
            )
        ''')
        db.execute('''
            CREATE TABLE IF NOT EXISTS orders (
                id TEXT PRIMARY KEY,
                user_email TEXT,
                customer_name TEXT NOT NULL,
                customer_email TEXT NOT NULL,
                address_line TEXT,
                city TEXT,
                postal_code TEXT,
                country TEXT,
                total REAL NOT NULL,
                created_at TEXT NOT NULL,
                status TEXT NOT NULL,
                FOREIGN KEY(user_email) REFERENCES users(email)
            )
        ''')
        db.execute('''
            CREATE TABLE IF NOT EXISTS order_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_id TEXT NOT NULL,
                product_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                price REAL NOT NULL,
                quantity INTEGER NOT NULL,
                item_total REAL NOT NULL,
                FOREIGN KEY(order_id) REFERENCES orders(id),
                FOREIGN KEY(product_id) REFERENCES products(id)
            )
        ''')
        db.execute('''
            CREATE TABLE IF NOT EXISTS shipping_rates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                rate_type TEXT NOT NULL,
                country TEXT,
                cost REAL NOT NULL
            )
        ''')
        db.execute('''
            CREATE TABLE IF NOT EXISTS payments (
                id TEXT PRIMARY KEY,
                order_id TEXT NOT NULL UNIQUE,
                stripe_payment_intent_id TEXT,
                amount REAL NOT NULL,
                currency TEXT DEFAULT 'usd',
                status TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY(order_id) REFERENCES orders(id)
            )
        ''')
        db.commit()
        seed_products()
        seed_shipping_rates()
        global DB_INITIALIZED
        DB_INITIALIZED = True


@app.before_request
def initialize_database():
    global DB_INITIALIZED
    if not DB_INITIALIZED:
        init_db()
        DB_INITIALIZED = True


def query_db(query, args=(), one=False):
    cur = get_db().execute(query, args)
    rv = cur.fetchall()
    cur.close()
    return (rv[0] if rv else None) if one else rv


def get_db_product(product_id):
    row = query_db(
        'SELECT id, name, description, price, inventory, category, image FROM products WHERE id = ?',
        (product_id,),
        one=True
    )
    return dict(row) if row else None


def get_products(search='', category=''):
    query = 'SELECT id, name, description, price, inventory, category, image FROM products'
    params = []
    filters = []
    if search:
        filters.append('(LOWER(name) LIKE ? OR LOWER(description) LIKE ? OR LOWER(category) LIKE ?)')
        params.extend([f'%{search.lower()}%'] * 3)
    if category:
        filters.append('LOWER(category) = ?')
        params.append(category.lower())
    if filters:
        query += ' WHERE ' + ' AND '.join(filters)
    query += ' ORDER BY name ASC'
    rows = query_db(query, params)
    return [dict(row) for row in rows]


def update_product_inventory(product_id, quantity):
    db = get_db()
    db.execute('UPDATE products SET inventory = inventory - ? WHERE id = ?', (quantity, product_id))
    db.commit()


def require_admin_key():
    key = request.headers.get('X-Admin-Key') or request.args.get('admin_key')
    return key == ADMIN_SEED_KEY


def get_current_user():
    return session.get('user_email')


def get_product_review_summary(product):
    rows = query_db(
        'SELECT rating FROM reviews WHERE product_id = ?',
        (product['id'],)
    )
    if not rows:
        return {**product, 'average_rating': 0.0, 'review_count': 0}
    total_rating = sum(row['rating'] for row in rows)
    average = round(total_rating / len(rows), 1)
    return {**product, 'average_rating': average, 'review_count': len(rows)}


def get_cart():
    return session.setdefault('cart', {})


@app.route('/')
def home():
    return render_template('index.html')


@app.route('/api/products')
def list_products():
    search = request.args.get('search', '').strip()
    category = request.args.get('category', '').strip()
    result = get_products(search, category)
    result = [get_product_review_summary(product) for product in result]
    return jsonify(result)


@app.route('/api/categories')
def list_categories():
    rows = query_db('SELECT DISTINCT category FROM products WHERE category IS NOT NULL AND category != ""')
    cats = sorted([row['category'] for row in rows if row['category']])
    return jsonify(cats)


@app.route('/api/products/<int:product_id>/reviews', methods=['GET'])
def list_reviews(product_id):
    product = get_db_product(product_id)
    if not product:
        return jsonify({'error': 'Product not found'}), 404
    sort_order = request.args.get('sort', 'newest')
    query = 'SELECT id, product_id, user_email, user_name, rating, comment, created_at FROM reviews WHERE product_id = ?'
    if sort_order == 'highest':
        query += ' ORDER BY rating DESC, created_at ASC'
    elif sort_order == 'oldest':
        query += ' ORDER BY created_at ASC'
    else:
        query += ' ORDER BY created_at DESC'
    rows = query_db(query, (product_id,))
    reviews = [dict(row) for row in rows]
    return jsonify(reviews)


@app.route('/api/products/<int:product_id>/reviews', methods=['POST'])
def post_review(product_id):
    user_email = get_current_user()
    if not user_email:
        return jsonify({'error': 'Authentication required'}), 401
    data = request.json or {}
    rating = int(data.get('rating', 0))
    comment = data.get('comment', '').strip()
    if rating < 1 or rating > 5:
        return jsonify({'error': 'Rating must be 1-5'}), 400
    if not comment:
        return jsonify({'error': 'Comment is required'}), 400
    product = get_db_product(product_id)
    if not product:
        return jsonify({'error': 'Product not found'}), 404
    user = query_db('SELECT email, name FROM users WHERE email = ?', (user_email,), one=True)
    if not user:
        return jsonify({'error': 'User not found'}), 401
    review_id = str(uuid.uuid4())[:8]
    created_at = datetime.now().isoformat()
    db = get_db()
    db.execute(
        'INSERT INTO reviews (id, product_id, user_email, user_name, rating, comment, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)',
        (review_id, product_id, user_email, user['name'], rating, comment, created_at)
    )
    db.commit()
    review = {
        'id': review_id,
        'product_id': product_id,
        'user_email': user_email,
        'user_name': user['name'],
        'rating': rating,
        'comment': comment,
        'created_at': created_at,
    }
    return jsonify(review), 201


@app.route('/api/auth/signup', methods=['POST'])
def signup():
    data = request.json or {}
    email = data.get('email', '').strip().lower()
    password = data.get('password', '').strip()
    name = data.get('name', '').strip()
    
    if not email or not password or not name:
        return jsonify({'error': 'Missing email, password, or name'}), 400
    existing = query_db('SELECT email FROM users WHERE email = ?', (email,), one=True)
    if existing:
        return jsonify({'error': 'Email already registered'}), 409
    
    db = get_db()
    db.execute('INSERT INTO users (email, password, name) VALUES (?, ?, ?)', (email, password, name))
    db.commit()
    session['user_email'] = email
    return jsonify({'success': True, 'user': {'email': email, 'name': name}}), 201


@app.route('/api/auth/login', methods=['POST'])
def login():
    data = request.json or {}
    email = data.get('email', '').strip().lower()
    password = data.get('password', '').strip()
    
    user = query_db('SELECT email, password, name FROM users WHERE email = ?', (email,), one=True)
    if not user or user['password'] != password:
        return jsonify({'error': 'Invalid email or password'}), 401
    
    session['user_email'] = email
    return jsonify({'success': True, 'user': {'email': email, 'name': user['name']}})


@app.route('/api/auth/logout', methods=['POST'])
def logout():
    session.pop('user_email', None)
    session['cart'] = {}
    return jsonify({'success': True})


@app.route('/api/auth/me', methods=['GET'])
def get_me():
    email = get_current_user()
    if not email:
        return jsonify(None)
    user = query_db('SELECT email, name FROM users WHERE email = ?', (email,), one=True)
    if user:
        return jsonify({'email': email, 'name': user['name']})
    return jsonify(None)


@app.route('/api/cart', methods=['GET'])
def get_cart_api():
    cart = get_cart()
    items = []
    total = 0.0
    for product_id_str, quantity in cart.items():
        product_id = int(product_id_str)
        product = get_db_product(product_id)
        if product:
            item_total = product['price'] * quantity
            total += item_total
            items.append({
                'id': product['id'],
                'name': product['name'],
                'price': product['price'],
                'quantity': quantity,
                'item_total': round(item_total, 2),
            })
    return jsonify({'items': items, 'total': round(total, 2)})


@app.route('/api/cart/add', methods=['POST'])
def add_to_cart():
    data = request.json or {}
    product_id = int(data.get('product_id', 0))
    quantity = int(data.get('quantity', 1))
    product = get_db_product(product_id)
    if product is None:
        return jsonify({'error': 'Product not found'}), 404
    current_quantity = get_cart().get(str(product_id), 0)
    new_quantity = current_quantity + quantity
    if new_quantity > product['inventory']:
        return jsonify({'error': 'Not enough inventory available'}), 400
    cart = get_cart()
    if new_quantity <= 0:
        cart.pop(str(product_id), None)
    else:
        cart[str(product_id)] = new_quantity
    session['cart'] = cart
    return jsonify({'success': True, 'cart': cart})


@app.route('/api/cart/remove', methods=['POST'])
def remove_from_cart():
    data = request.json or {}
    product_id = int(data.get('product_id', 0))
    cart = get_cart()
    if str(product_id) in cart:
        del cart[str(product_id)]
        session['cart'] = cart
        return jsonify({'success': True, 'cart': cart})
    return jsonify({'error': 'Item not in cart'}), 404


@app.route('/api/checkout', methods=['POST'])
def checkout():
    data = request.json or {}
    # require logged-in user to checkout
    user_email = get_current_user()
    if not user_email:
        return jsonify({'error': 'Authentication required'}), 401

    user = query_db('SELECT name FROM users WHERE email = ?', (user_email,), one=True)
    if not user:
        return jsonify({'error': 'Authenticated user not found'}), 401

    customer_name = data.get('customer_name') or user['name']
    customer_email = data.get('customer_email') or user_email

    # optional shipping/address fields
    shipping_address = {
        'address_line': data.get('address_line', ''),
        'city': data.get('city', ''),
        'postal_code': data.get('postal_code', ''),
        'country': data.get('country', ''),
    }

    # server-side validation: require city and postal_code
    missing = []
    if not shipping_address['city'].strip():
        missing.append('city')
    if not shipping_address['postal_code'].strip():
        missing.append('postal_code')
    if missing:
        return jsonify({'error': 'Missing required shipping fields', 'missing': missing}), 400

    cart = get_cart()
    if not cart:
        return jsonify({'error': 'Cart is empty'}), 400
    
    items = []
    total = 0.0
    for product_id_str, quantity in cart.items():
        product_id = int(product_id_str)
        product = get_db_product(product_id)
        if not product:
            return jsonify({'error': f'Product {product_id} not found'}), 404
        if product['inventory'] < quantity:
            return jsonify({'error': f'Insufficient inventory for {product["name"]}'}), 400
        item_total = product['price'] * quantity
        total += item_total
        items.append({
            'id': product['id'],
            'name': product['name'],
            'price': product['price'],
            'quantity': quantity,
            'item_total': round(item_total, 2),
        })
    
    user_email = get_current_user()
    order_id = str(uuid.uuid4())[:8]
    created_at = datetime.now().isoformat()
    db = get_db()
    db.execute(
        'INSERT INTO orders (id, user_email, customer_name, customer_email, address_line, city, postal_code, country, total, created_at, status) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
        (order_id, user_email, customer_name, customer_email, shipping_address['address_line'], shipping_address['city'], shipping_address['postal_code'], shipping_address['country'], round(total, 2), created_at, 'pending')
    )
    for item in items:
        db.execute(
            'INSERT INTO order_items (order_id, product_id, name, price, quantity, item_total) VALUES (?, ?, ?, ?, ?, ?)',
            (order_id, item['id'], item['name'], item['price'], item['quantity'], item['item_total'])
        )
        db.execute('UPDATE products SET inventory = inventory - ? WHERE id = ?', (item['quantity'], item['id']))
    db.commit()
    session['cart'] = {}

    order = {
        'id': order_id,
        'user_email': user_email,
        'customer_name': customer_name,
        'customer_email': customer_email,
        'shipping_address': shipping_address,
        'items': items,
        'total': round(total, 2),
        'created_at': created_at,
        'status': 'pending',
    }

    return jsonify({'success': True, 'order': order}), 201


@app.route('/api/orders', methods=['GET'])
def list_orders():
    user_email = get_current_user()
    if user_email:
        rows = query_db('''
            SELECT o.id, o.user_email, o.customer_name, o.customer_email, o.total, o.created_at, o.status,
                   COUNT(oi.id) AS item_count
            FROM orders o
            LEFT JOIN order_items oi ON o.id = oi.order_id
            WHERE o.user_email = ?
            GROUP BY o.id
            ORDER BY o.created_at DESC
        ''', (user_email,))
    else:
        rows = query_db('''
            SELECT o.id, o.user_email, o.customer_name, o.customer_email, o.total, o.created_at, o.status,
                   COUNT(oi.id) AS item_count
            FROM orders o
            LEFT JOIN order_items oi ON o.id = oi.order_id
            GROUP BY o.id
            ORDER BY o.created_at DESC
        ''')
    orders = [dict(row) for row in rows]
    return jsonify(orders)


@app.route('/api/orders/<order_id>', methods=['GET'])
def get_order(order_id):
    order_row = query_db('SELECT id, user_email, customer_name, customer_email, address_line, city, postal_code, country, total, created_at, status FROM orders WHERE id = ?', (order_id,), one=True)
    if order_row is None:
        return jsonify({'error': 'Order not found'}), 404
    items = query_db('SELECT product_id AS id, name, price, quantity, item_total FROM order_items WHERE order_id = ?', (order_id,))
    order = dict(order_row)
    order['items'] = [dict(item) for item in items]
    order['shipping_address'] = {
        'address_line': order['address_line'],
        'city': order['city'],
        'postal_code': order['postal_code'],
        'country': order['country'],
    }
    return jsonify(order)


def get_count(table_name):
    row = query_db(f'SELECT COUNT(*) AS count FROM {table_name}', one=True)
    return row['count'] if row else 0


@app.route('/api/persistence-status', methods=['GET'])
def persistence_status():
    return jsonify({
        'db_file': os.path.basename(DATABASE),
        'users': get_count('users'),
        'reviews': get_count('reviews'),
        'orders': get_count('orders'),
        'order_items': get_count('order_items'),
    })


def seed_database_payload():
    seed_products()
    db = get_db()
    created = {'user': False, 'review': False, 'order': False}

    if not query_db('SELECT email FROM users WHERE email = ?', ('demo@example.com',), one=True):
        db.execute(
            'INSERT INTO users (email, password, name) VALUES (?, ?, ?)',
            ('demo@example.com', 'password', 'Demo User')
        )
        created['user'] = True

    if not query_db('SELECT 1 FROM reviews LIMIT 1', one=True):
        db.execute(
            'INSERT INTO reviews (id, product_id, user_email, user_name, rating, comment, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)',
            (str(uuid.uuid4())[:8], 1, 'demo@example.com', 'Demo User', 5, 'Amazing headphones with crisp sound.', datetime.now().isoformat())
        )
        created['review'] = True

    if not query_db('SELECT 1 FROM orders LIMIT 1', one=True):
        order_id = str(uuid.uuid4())[:8]
        created_at = datetime.now().isoformat()
        db.execute(
            'INSERT INTO orders (id, user_email, customer_name, customer_email, address_line, city, postal_code, country, total, created_at, status) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
            (order_id, 'demo@example.com', 'Demo User', 'demo@example.com', '123 Demo Lane', 'Demo City', '12345', 'Demo Country', 149.99, created_at, 'pending')
        )
        db.execute(
            'INSERT INTO order_items (order_id, product_id, name, price, quantity, item_total) VALUES (?, ?, ?, ?, ?, ?)',
            (order_id, 1, 'Wireless Headphones', 100.00, 1, 100.00)
        )
        db.execute(
            'INSERT INTO order_items (order_id, product_id, name, price, quantity, item_total) VALUES (?, ?, ?, ?, ?, ?)',
            (order_id, 2, 'Smart Speaker', 49.99, 1, 49.99)
        )
        created['order'] = True

    if any(created.values()):
        db.commit()
        status_code = 201
    else:
        status_code = 200

    counts = {
        'users': get_count('users'),
        'reviews': get_count('reviews'),
        'orders': get_count('orders'),
        'order_items': get_count('order_items'),
    }

    return {'seeded': any(created.values()), 'created': created, 'counts': counts}, status_code


@app.route('/api/seed-database', methods=['POST'])
def seed_database():
    payload, status_code = seed_database_payload()
    return jsonify(payload), status_code


@app.route('/api/admin/seed-database', methods=['POST'])
def admin_seed_database():
    if not require_admin_key():
        return jsonify({'error': 'Unauthorized'}), 401
    payload, status_code = seed_database_payload()
    return jsonify(payload), status_code


# Admin Product Management Routes
@app.route('/api/admin/products', methods=['GET'])
def admin_list_products():
    if not require_admin_key():
        return jsonify({'error': 'Unauthorized'}), 401
    products = get_products()
    for product in products:
        product = get_product_review_summary(product)
    return jsonify(products)


@app.route('/api/admin/products', methods=['POST'])
def admin_create_product():
    if not require_admin_key():
        return jsonify({'error': 'Unauthorized'}), 401
    data = request.json or {}
    name = data.get('name', '').strip()
    description = data.get('description', '').strip()
    price = data.get('price')
    inventory = data.get('inventory')
    category = data.get('category', '').strip()
    image = data.get('image', '').strip()
    
    if not name or not description or price is None or inventory is None:
        return jsonify({'error': 'Name, description, price, and inventory are required'}), 400
    
    try:
        price = float(price)
        inventory = int(inventory)
        if price < 0 or inventory < 0:
            return jsonify({'error': 'Price and inventory must be non-negative'}), 400
    except (ValueError, TypeError):
        return jsonify({'error': 'Price must be a number and inventory must be an integer'}), 400
    
    db = get_db()
    cursor = db.execute(
        'INSERT INTO products (name, description, price, inventory, category, image) VALUES (?, ?, ?, ?, ?, ?)',
        (name, description, price, inventory, category, image)
    )
    db.commit()
    product_id = cursor.lastrowid
    product = get_db_product(product_id)
    return jsonify(product), 201


@app.route('/api/admin/products/<int:product_id>', methods=['PUT'])
def admin_update_product(product_id):
    if not require_admin_key():
        return jsonify({'error': 'Unauthorized'}), 401
    
    product = get_db_product(product_id)
    if not product:
        return jsonify({'error': 'Product not found'}), 404
    
    data = request.json or {}
    name = data.get('name', product['name']).strip()
    description = data.get('description', product['description']).strip()
    price = data.get('price', product['price'])
    inventory = data.get('inventory', product['inventory'])
    category = data.get('category', product['category']).strip()
    image = data.get('image', product['image']).strip()
    
    if not name or not description:
        return jsonify({'error': 'Name and description are required'}), 400
    
    try:
        price = float(price)
        inventory = int(inventory)
        if price < 0 or inventory < 0:
            return jsonify({'error': 'Price and inventory must be non-negative'}), 400
    except (ValueError, TypeError):
        return jsonify({'error': 'Price must be a number and inventory must be an integer'}), 400
    
    db = get_db()
    db.execute(
        'UPDATE products SET name = ?, description = ?, price = ?, inventory = ?, category = ?, image = ? WHERE id = ?',
        (name, description, price, inventory, category, image, product_id)
    )
    db.commit()
    updated_product = get_db_product(product_id)
    return jsonify(updated_product)


@app.route('/api/admin/products/<int:product_id>', methods=['DELETE'])
def admin_delete_product(product_id):
    if not require_admin_key():
        return jsonify({'error': 'Unauthorized'}), 401
    
    product = get_db_product(product_id)
    if not product:
        return jsonify({'error': 'Product not found'}), 404
    
    db = get_db()
    db.execute('DELETE FROM reviews WHERE product_id = ?', (product_id,))
    db.execute('DELETE FROM order_items WHERE product_id = ?', (product_id,))
    db.execute('DELETE FROM products WHERE id = ?', (product_id,))
    db.commit()
    return jsonify({'message': 'Product deleted successfully'})


# Shipping and Payment Routes
@app.route('/api/shipping-rates', methods=['GET'])
def get_shipping_rates():
    rows = query_db('SELECT DISTINCT rate_type FROM shipping_rates')
    rate_types = [row['rate_type'] for row in rows]
    return jsonify({'available_types': rate_types})


@app.route('/api/shipping/calculate', methods=['POST'])
def calculate_shipping():
    data = request.json or {}
    country = data.get('country', 'Other').strip()
    shipping_method = data.get('method', 'flat')
    
    if shipping_method == 'flat':
        rate = query_db(
            'SELECT cost FROM shipping_rates WHERE rate_type = ? AND country IS NULL',
            ('flat',),
            one=True
        )
    else:  # zone-based
        rate = query_db(
            'SELECT cost FROM shipping_rates WHERE rate_type = ? AND (country = ? OR country = ?)',
            ('zone', country, 'Other'),
            one=True
        )
        if not rate:
            rate = query_db(
                'SELECT cost FROM shipping_rates WHERE rate_type = ? AND country = ?',
                ('zone', 'Other'),
                one=True
            )
    
    cost = rate['cost'] if rate else 9.99
    return jsonify({'shipping_cost': cost, 'method': shipping_method, 'country': country})


@app.route('/api/payment/intent', methods=['POST'])
def create_payment_intent():
    if not stripe:
        return jsonify({'error': 'Stripe not configured'}), 500
    
    data = request.json or {}
    cart_items = data.get('cart', {})
    shipping_cost = float(data.get('shipping_cost', 0))
    customer_email = data.get('customer_email', '').strip()
    
    if not customer_email or not cart_items:
        return jsonify({'error': 'Email and cart items required'}), 400
    
    # Calculate total
    total_cents = 0
    for product_id_str, quantity in cart_items.items():
        product_id = int(product_id_str)
        product = get_db_product(product_id)
        if product and product['inventory'] >= quantity:
            total_cents += int(product['price'] * quantity * 100)
        else:
            return jsonify({'error': f'Product {product_id} out of stock'}), 400
    
    total_cents += int(shipping_cost * 100)
    
    try:
        intent = stripe.PaymentIntent.create(
            amount=total_cents,
            currency='usd',
            receipt_email=customer_email,
            metadata={'order_type': 'ecommerce'}
        )
        return jsonify({
            'client_secret': intent.client_secret,
            'payment_intent_id': intent.id,
            'amount': total_cents / 100
        })
    except stripe.error.CardError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': 'Payment processing error'}), 500


@app.route('/api/payment/confirm', methods=['POST'])
def confirm_payment():
    data = request.json or {}
    payment_intent_id = data.get('payment_intent_id', '').strip()
    customer_name = data.get('customer_name', '').strip()
    customer_email = data.get('customer_email', '').strip()
    address_line = data.get('address_line', '').strip()
    city = data.get('city', '').strip()
    postal_code = data.get('postal_code', '').strip()
    country = data.get('country', '').strip()
    shipping_cost = float(data.get('shipping_cost', 0))
    
    if not all([payment_intent_id, customer_name, customer_email, city, postal_code]):
        return jsonify({'error': 'Missing required fields'}), 400
    
    try:
        if stripe:
            intent = stripe.PaymentIntent.retrieve(payment_intent_id)
            if intent.status != 'succeeded':
                return jsonify({'error': 'Payment not completed'}), 400
        
        cart = session.get('cart', {})
        if not cart:
            return jsonify({'error': 'Cart is empty'}), 400
        
        db = get_db()
        order_id = str(uuid.uuid4())[:8]
        created_at = datetime.now().isoformat()
        
        # Calculate order total
        order_total = shipping_cost
        for product_id_str, quantity in cart.items():
            product_id = int(product_id_str)
            product = get_db_product(product_id)
            if product and product['inventory'] >= quantity:
                order_total += product['price'] * quantity
                update_product_inventory(product_id, quantity)
                db.execute(
                    'INSERT INTO order_items (order_id, product_id, name, price, quantity, item_total) VALUES (?, ?, ?, ?, ?, ?)',
                    (order_id, product_id, product['name'], product['price'], quantity, product['price'] * quantity)
                )
            else:
                return jsonify({'error': f'Product {product_id} out of stock'}), 400
        
        user_email = get_current_user()
        db.execute(
            'INSERT INTO orders (id, user_email, customer_name, customer_email, address_line, city, postal_code, country, total, created_at, status) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
            (order_id, user_email, customer_name, customer_email, address_line, city, postal_code, country, order_total, created_at, 'pending')
        )
        
        # Record payment
        payment_id = str(uuid.uuid4())[:8]
        db.execute(
            'INSERT INTO payments (id, order_id, stripe_payment_intent_id, amount, status, created_at) VALUES (?, ?, ?, ?, ?, ?)',
            (payment_id, order_id, payment_intent_id, order_total, 'succeeded', created_at)
        )
        
        db.commit()
        session['cart'] = {}
        
        return jsonify({
            'order_id': order_id,
            'status': 'success',
            'total': order_total,
            'message': 'Order created successfully'
        }), 201
    
    except Exception as e:
        return jsonify({'error': 'Failed to confirm payment'}), 500


# Analytics Routes
@app.route('/api/analytics/overview', methods=['GET'])
def analytics_overview():
    # Total orders and revenue
    orders_row = query_db('SELECT COUNT(*) as count, SUM(total) as revenue FROM orders', one=True)
    total_orders = orders_row['count'] or 0
    total_revenue = orders_row['revenue'] or 0.0
    avg_order_value = total_revenue / total_orders if total_orders > 0 else 0.0
    
    # Total customers
    customers_row = query_db('SELECT COUNT(DISTINCT email) as count FROM users WHERE email != ?', ('admin@example.com',), one=True)
    total_customers = customers_row['count'] or 0
    
    # Revenue trend (last 7 days grouped by day)
    trend = query_db('''
        SELECT DATE(created_at) as day, SUM(total) as revenue, COUNT(*) as orders
        FROM orders
        WHERE created_at >= datetime('now', '-7 days')
        GROUP BY DATE(created_at)
        ORDER BY day ASC
    ''')
    
    return jsonify({
        'total_orders': total_orders,
        'total_revenue': round(total_revenue, 2),
        'avg_order_value': round(avg_order_value, 2),
        'total_customers': total_customers,
        'revenue_trend': [{'day': row['day'], 'revenue': row['revenue'], 'orders': row['orders']} for row in trend]
    })


@app.route('/api/analytics/products', methods=['GET'])
def analytics_products():
    # Top products by revenue
    products = query_db('''
        SELECT p.id, p.name, p.inventory,
               COUNT(oi.id) as units_sold,
               SUM(oi.item_total) as revenue
        FROM products p
        LEFT JOIN order_items oi ON p.id = oi.product_id
        GROUP BY p.id
        ORDER BY revenue DESC NULLS LAST
        LIMIT 10
    ''')
    
    return jsonify([{
        'id': row['id'],
        'name': row['name'],
        'units_sold': row['units_sold'] or 0,
        'revenue': round(row['revenue'] or 0, 2),
        'inventory': row['inventory']
    } for row in products])


@app.route('/api/analytics/customers', methods=['GET'])
def analytics_customers():
    # Customer metrics
    customers_row = query_db('SELECT COUNT(DISTINCT email) as count FROM users WHERE email != ?', ('admin@example.com',), one=True)
    total_customers = customers_row['count'] or 0
    
    # Repeat customers (customers with 2+ orders)
    repeat = query_db('''
        SELECT COUNT(*) as count FROM (
            SELECT user_email, COUNT(*) as order_count
            FROM orders
            WHERE user_email IS NOT NULL
            GROUP BY user_email
            HAVING order_count > 1
        )
    ''', one=True)
    repeat_customers = repeat['count'] or 0
    repeat_rate = (repeat_customers / total_customers * 100) if total_customers > 0 else 0
    
    # Average orders per customer
    orders_row = query_db('SELECT COUNT(*) as count FROM orders', one=True)
    total_orders = orders_row['count'] or 0
    avg_orders = (total_orders / total_customers) if total_customers > 0 else 0
    
    # Top customers by spending
    top_customers = query_db('''
        SELECT u.email, u.name,
               COUNT(o.id) as order_count,
               SUM(o.total) as total_spent
        FROM orders o
        JOIN users u ON o.user_email = u.email
        WHERE o.user_email IS NOT NULL
        GROUP BY o.user_email
        ORDER BY total_spent DESC
        LIMIT 10
    ''')
    
    return jsonify({
        'total_customers': total_customers,
        'repeat_customers': repeat_customers,
        'repeat_rate': round(repeat_rate, 1),
        'avg_orders_per_customer': round(avg_orders, 2),
        'top_customers': [{
            'name': row['name'],
            'email': row['email'],
            'order_count': row['order_count'],
            'total_spent': round(row['total_spent'], 2)
        } for row in top_customers]
    })


@app.route('/api/analytics/revenue', methods=['GET'])
def analytics_revenue():
    # Revenue metrics
    orders_row = query_db('SELECT COUNT(*) as count, SUM(total) as revenue FROM orders', one=True)
    total_orders = orders_row['count'] or 0
    total_revenue = orders_row['revenue'] or 0.0
    avg_order_value = total_revenue / total_orders if total_orders > 0 else 0.0
    
    # Average items per order
    items_row = query_db('''
        SELECT AVG(item_count) as avg_items FROM (
            SELECT COUNT(*) as item_count FROM order_items GROUP BY order_id
        )
    ''', one=True)
    avg_items = items_row['avg_items'] or 0
    
    # Daily revenue (last 14 days)
    daily_revenue = query_db('''
        SELECT DATE(created_at) as day, SUM(total) as revenue, COUNT(*) as orders
        FROM orders
        WHERE created_at >= datetime('now', '-14 days')
        GROUP BY DATE(created_at)
        ORDER BY day ASC
    ''')
    
    return jsonify({
        'total_revenue': round(total_revenue, 2),
        'total_orders': total_orders,
        'avg_order_value': round(avg_order_value, 2),
        'avg_items_per_order': round(avg_items, 2),
        'daily_revenue': [{'day': row['day'], 'revenue': row['revenue'], 'orders': row['orders']} for row in daily_revenue]
    })


if __name__ == '__main__':
    init_db()
    app.run(debug=True)
