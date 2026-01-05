from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_mysqldb import MySQL
from flask_cors import CORS
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import os
import MySQLdb.cursors
from dotenv import load_dotenv
import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
<<<<<<< HEAD
import requests
=======
>>>>>>> d0402177e59f186b5c38041209e3226255a712df


load_dotenv()

app = Flask(__name__)
CORS(app)


app.config['MYSQL_HOST'] = os.getenv('MYSQL_HOST')
app.config['MYSQL_USER'] = os.getenv('MYSQL_USER')
app.config['MYSQL_PASSWORD'] = os.getenv('MYSQL_PASSWORD')
app.config['MYSQL_DB'] = os.getenv('MYSQL_DB')
app.config['MYSQL_PORT'] = int(os.getenv('MYSQL_PORT', 3306))

app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET_KEY')
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
app.config['APP_URL'] = os.getenv('APP_URL')
app.config['API_KEY'] = os.getenv('API_KEY')
app.config['API_SECRET'] = os.getenv('API_SECRET')



app.config['SENDER'] = os.getenv('SENDER')
app.config['PASSWORD'] = os.getenv('PASSWORD')



jwt = JWTManager(app)



app.config['fir_tech']=os.getenv('SENDER')
app.config['sec_tech']=os.getenv('PASSWORD')

log_filename = "script.log"
logging.basicConfig(
    filename=log_filename,
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s: %(message)s",
)

mysql=MySQL(app)

def get_db_cursor(dictionary=False):
    """Return MySQL cursor"""
    if dictionary:
        return mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    return mysql.connection.cursor()

@app.route('/testdb')    # end_point   app url ->  google.com
def test_db():
    try:
        cur = mysql.connection.cursor()
        cur.execute("SELECT 1")
        logging.info("hello")     
        #print("DB")
        return "DB Connected!"
    except Exception as e:
        return {"error": str(e)},400 
    

@app.route('/',methods=['GET'])
def home():
    data={"message":"welcome to Jewell_shop shreya ","name":"shirish"}
    return jsonify(data),200
    
    
@app.route('/protected', methods=['GET'])
@jwt_required()
def protected():
    current_user = get_jwt_identity()
    print(current_user)
    return jsonify(logged_in_as=current_user)

@app.route('/register', methods=['POST'])
def register():
    """
    Register a new user
    Fields: user_id, username, email, password
    Returns: JWT token
    """
    try:
        data = request.get_json()
        user_id = data.get('user_id')
        username = data.get('username')
        email = data.get('email')
        password = data.get('password')

        if not username or not email or not password:
            return jsonify({"error": "All fields are required"}), 400

        # Check if user already exists
        cursor = get_db_cursor(dictionary=True)
        cursor.execute(
            "SELECT * FROM users WHERE username=%s OR email=%s",
            (username, email)
        )
        if cursor.fetchone():
            cursor.close()
            return jsonify({"message": "User already exists. Please login."}), 409
        cursor.close()

        # Hash password
        hashed_password = generate_password_hash(password)

        # Insert new user
        cursor = get_db_cursor()
        cursor.execute(
            "INSERT INTO users (user_id, username, password, org_password, email) VALUES (%s,%s,%s,%s,%s)",
            (user_id, username, hashed_password, password, email)
        )
        mysql.connection.commit()
        cursor.close()

<<<<<<< HEAD
        logging.info("New user registered: {username} ({email})")

        # ---------------- SMTP EMAIL LOGIC (ADDED) ----------------

        sender_email = app.config['SENDER']
        sender_password = app.config['PASSWORD']

=======
        logging.info(f"New user registered: {username} ({email})")

        # ---------------- SMTP EMAIL LOGIC (ADDED) ----------------

        sender_email = app.config['fir_tech']
        sender_password = app.config['sec_tech']
>>>>>>> d0402177e59f186b5c38041209e3226255a712df
        subject = "Warm Welcome from Shirish and it's team side"
        logging.info(email)
        data_want_send = MIMEMultipart()
        data_want_send['From'] = sender_email
        data_want_send['To'] = email
        data_want_send['Subject'] = subject

        body = '''Hi,

My name is Shirish, I am the CEO of hekratech.pvt.lim.
This is an automated email, but if you reply it will go straight to me.

If you have any feedback or comments on our product I would love to hear it.
If you are considering using this website, please get in touch.
We would be happy to assist you.

Thanks,
Shirish Dwivedi
'''
        data_want_send.attach(MIMEText(body, 'plain'))

        try:
            server = smtplib.SMTP('smtp.gmail.com', 587)
            server.starttls()
            server.login(sender_email, sender_password)
            server.sendmail(sender_email, email, data_want_send.as_string())
            server.close()
            logging.info("Welcome email sent successfully")
        except Exception as e:
            logging.error(f"Email sending failed: {str(e)}")

        # ----------------------------------------------------------

        access_token = create_access_token(identity=user_id)

        return jsonify({
            "message": "User registered successfully!",
            "access_token": access_token
        }), 201

    except Exception as e:
        return jsonify({
            "message": "Registration failed",
            "error": str(e)
        }), 500


@app.route('/login', methods=['POST'])
def login():
    """
    Login user
    Fields: email, password
    Returns: JWT token + user info
    """
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')

    if not email or not password:
        return jsonify({"error": "Email and password required"}), 400

    cursor = get_db_cursor(dictionary=True)
    cursor.execute("SELECT * FROM users WHERE email=%s", (email,))
    user = cursor.fetchone()
    cursor.close()

    if user and check_password_hash(user['password'], password):
        
        access_token = create_access_token(identity=user['user_id'])
        logging.info(f"User logged in: {user['username']} ({user['email']})")
        return jsonify({
            "access_token": access_token,
            "user": {
                "id": user['username'],
                "email": user['email']
            }
        }), 200

    return jsonify({"msg": "Invalid email or password"}), 401




@app.route('/profile', methods=['GET'])
@jwt_required()
def get_profile():
    """
    Get user profile
    Returns: user info
    """
    user_id = get_jwt_identity()
    cursor = get_db_cursor(dictionary=True)
    cursor.execute("SELECT user_id, username, email FROM users WHERE user_id=%s", (user_id,))
    user = cursor.fetchone()
    cursor.close()
    return jsonify(user), 200

def get_current_gold_rate():
    url = "https://api.metalpriceapi.com/v1/latest?api_key=25d798ade854da6d5d58b410b72a5e89&base=INR&currencies=XAU"
    response = requests.get(url)
    data = response.json()

    # XAU is per ounce
    price_per_gram = (1 / data["rates"]["XAU"]) / 31.1035
    return round(price_per_gram, 2)



def get_current_silver_rate():
    url = "https://api.metalpriceapi.com/v1/latest?api_key=25d798ade854da6d5d58b410b72a5e89&base=INR&currencies=XAG"
    response = requests.get(url)
    data = response.json()

    # XAG is per ounce
    price_per_gram = (1 / data["rates"]["XAG"]) / 31.1035
    return round(price_per_gram, 2)



@app.route('/calculate_price', methods=['POST'])     # not  used api / only for testing
@jwt_required()
def calculate_price():
    data = request.get_json()

    quantity = data.get('quantity')

    if not quantity:
        return jsonify({"error": "Quantity is required"}), 400

    gold_price_per_gram = get_current_gold_rate()
    logging.info(gold_price_per_gram)
    final_price = gold_price_per_gram * quantity

    return jsonify({
        "gold_price_per_gram": gold_price_per_gram,
        "quantity": quantity,
        "final_price": final_price
    }), 200


@app.route('/products', methods=['POST'])
@jwt_required()
def create_product():
    """
    Admin only
    Fields: name, category, price, description, stock, images
    """
    data = request.get_json()
    qnt = data.get("quantity")  
    mt_cat=data.get("metal_cat")  # "Gold "  or "Silver"

    logging.info(mt_cat)

    final_price=0
    if mt_cat=="Gold":
        gold_price = get_current_gold_rate() 
        final_price = gold_price * qnt
    elif mt_cat=="Silver":
        silver_rate = get_current_silver_rate()
        final_price =silver_rate * qnt 

    cursor = get_db_cursor()
    cursor.execute("""
        INSERT INTO products (name, category, price, description, stock, images, quantity, metal_name)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
    """, (
        data['name'],
        data.get('category'),
        final_price,
        data.get('description'),
        data.get('stock'),
        data.get('images'),
        data.get('quantity'),
        mt_cat
    )
    )
    mysql.connection.commit()
    cursor.close()
    return jsonify({"msg": "Product created successfully"}), 201



@app.route('/products', methods=['GET'])
def get_products():
    # return jsonify([
    #     {
    #         "id": 1,
    #         "name": "Gold Coin",
    #         "price": "₹1,20,000",
    #         "image": "https://png.pngtree.com/png-clipart/20190520/original/pngtree-gold-coin-png-image_3779125.jpg"
    #     },
    #     {
    #         "id": 2,
    #         "name": "Silver Coin",
    #         "price": "₹6,000",
    #         "image": "https://silvera.co.in/app/uploaded/product/silvera-5784531681558188318.png"
    #     },
    #     {
    #         "id":3,
    #         "name": "Gold Necklace",
    #         "price": "₹6,999",
    #         "image": "https://m.media-amazon.com/images/I/711gUVvYePL._AC_UY300_.jpg"  
    #     }
    # ])
    """
    Get all products
    """
    cursor = get_db_cursor()
    cursor.execute("SELECT id, name, category, price, description, stock, images , quantity FROM products")
    products = cursor.fetchall()
    cursor.close()

    result = [
        {"id": p[0], "name": p[1], "category": p[2], "price": p[3],
         "description": p[4], "stock": p[5], "images": p[6], "quantity": p[7]} for p in products
    ]
    return jsonify(result), 200


<<<<<<< HEAD
=======

>>>>>>> d0402177e59f186b5c38041209e3226255a712df
@app.route('/products/<int:id>', methods=['GET'])
def get_product(id):
    """
    Get product by id
    """
    cursor = get_db_cursor()
    cursor.execute("SELECT id, name, category, price, description, stock, images FROM products WHERE id=%s", (id,))
    product = cursor.fetchone()
    cursor.close()

    if product:
        return jsonify({
            "id": product[0], "name": product[1], "category": product[2],
            "price": product[3], "description": product[4], "stock": product[5],
            "images": product[6]
        }), 200
    return jsonify({"message": "Product not found"}), 404



@app.route('/cart', methods=['POST'])
@jwt_required()
def add_to_cart():
    """
    Add product to cart
    Fields: product_id, quantity
    """
    user_id = get_jwt_identity()
    data = request.get_json()
    cursor = get_db_cursor()
    cursor.execute("""
        INSERT INTO cart (user_id, product_id, quantity) VALUES (%s,%s,%s)
        ON DUPLICATE KEY UPDATE quantity = quantity + %s
    """, (user_id, data['product_id'], data['quantity'], data['quantity']))
    mysql.connection.commit()
    cursor.close()
    return jsonify({"msg": "Added to cart"}), 201


@app.route('/cart', methods=['GET'])
@jwt_required()
def get_cart():
    """
    Get all cart items for user
    """
    user_id = get_jwt_identity()
    cursor = get_db_cursor()
    cursor.execute("""
        SELECT c.product_id, c.quantity, p.name, p.price, p.images
        FROM cart c JOIN products p ON c.product_id=p.id WHERE c.user_id=%s
    """, (user_id,))
    cart_items = cursor.fetchall()
    cursor.close()

    result = [{"product_id": i[0], "quantity": i[1], "name": i[2], "price": i[3], "images": i[4]} for i in cart_items]
    return jsonify(result), 200



@app.route('/cart/<int:product_id>', methods=['DELETE'])
@jwt_required()
def remove_from_cart(product_id):
    """
    Remove product from cart
    """
    user_id = get_jwt_identity()
    cursor = get_db_cursor()
    cursor.execute("DELETE FROM cart WHERE user_id=%s AND product_id=%s", (user_id, product_id))
    mysql.connection.commit()
    cursor.close()
    return jsonify({"msg": "Removed from cart"}), 200


@app.route('/orders', methods=['POST'])
@jwt_required()
def create_order():
    """
    Create order from cart
    Fields: address, payment_method
    """
    user_id = get_jwt_identity()
    data = request.get_json()
    cursor = get_db_cursor()
    
    cursor.execute("SELECT product_id, quantity FROM cart WHERE user_id=%s", (user_id,))
    cart_items = cursor.fetchall()
    if not cart_items:
        return jsonify({"msg": "Cart is empty"}), 400

    
    cursor.execute("INSERT INTO orders (user_id, address, payment_method, status, created_at) VALUES (%s,%s,%s,'Pending',NOW())",
                   (user_id, data['address'], data['payment_method']))
    order_id = cursor.lastrowid

    
    for item in cart_items:
        cursor.execute("INSERT INTO order_items (order_id, product_id, quantity) VALUES (%s,%s,%s)",
                       (order_id, item[0], item[1]))

    
    cursor.execute("DELETE FROM cart WHERE user_id=%s", (user_id,))
    
    mysql.connection.commit()
    cursor.close()
    return jsonify({"msg": "Order placed successfully", "order_id": order_id}), 201


@app.route('/orders', methods=['GET'])
@jwt_required()
def get_orders():
    """
    Get all orders for a user
    """
    user_id = get_jwt_identity()
    cursor = get_db_cursor()
    cursor.execute("SELECT id, address, payment_method, status, created_at FROM orders WHERE user_id=%s", (user_id,))
    orders = cursor.fetchall()
    cursor.close()

    result = [{"id": o[0], "address": o[1], "payment_method": o[2], "status": o[3], "created_at": str(o[4])} for o in orders]
    return jsonify(result), 200



@app.route('/categories', methods=['GET'])
def get_categories():
    """
    Get all product categories
    """
    cursor = get_db_cursor()
    cursor.execute("SELECT DISTINCT category FROM products")
    categories = [c[0] for c in cursor.fetchall()]
    cursor.close()
    return jsonify(categories), 200


@app.route('/products/category/<string:category>', methods=['GET'])
def get_products_by_category(category):
    """
    Get products by category
    """
    cursor = get_db_cursor()
    cursor.execute("SELECT id, name, price, images FROM products WHERE category=%s", (category,))
    products = cursor.fetchall()
    cursor.close()
    result = [{"id": p[0], "name": p[1], "price": p[2], "images": p[3]} for p in products]
    return jsonify(result), 200



@app.route('/sendmail',methods=['POST'])
def send_mail():
    try:
        data=request.get_json()
        name=data.get('name')
        mobile=data.get('mobile')
        email=data.get('email')
        subject = data.get('subject')
        message=data.get('message')
        
        
        sender_email = app.config['fir_tech']
        sender_password = app.config['sec_tech']
        
        
        logging.info(email)
        data_want_send = MIMEMultipart()
        data_want_send['From'] = sender_email
        data_want_send['To'] = "shiridivedi951@gmail.com"
        data_want_send['Subject'] = subject

        body = f"My name is {name} and my Contact_no is {mobile}, please review my query and reply this mail as soon as possibile, " + message
        
        data_want_send.attach(MIMEText(body, 'plain'))

        try:
            server = smtplib.SMTP('smtp.gmail.com', 587)
            server.starttls()
            server.login(sender_email, sender_password)
            server.sendmail(sender_email, "shirishdivedi951@gmail.com", data_want_send.as_string())
            server.close()
            logging.info("Welcome email sent successfully")
            return jsonify({"msg":"Welcome email sent successfully"}),200
        except Exception as e:
            logging.error(f"Email sending failed: {str(e)}")
            return jsonify({"msg":"Email sending failed"}),400
    except  Exception as e:
        logging.error(f"Not Connected : {str(e)}")
        return jsonify({"msg":"Internal Server Error"}),500
        
        


@app.route('/api/contact', methods=['POST'])
def submit_contact():
    """Handle contact form submissions"""
    try:
        data = request.get_json()

        # Validate required fields
        if not data.get('name') or not data.get('email') or not data.get('message'):
            return jsonify({'error': 'Missing required fields'}), 400

        # Insert into database
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('''
            INSERT INTO contacts (name, email, phone, message, status)
            VALUES (%s, %s, %s, %s, %s)
        ''', (
            data['name'],
            data['email'],
            data.get('phone', ''),
            data['message'],
            'new'
        ))
        mysql.connection.commit()

        contact_id = cursor.lastrowid
        cursor.close()

        return jsonify({
            'message': 'Contact form submitted successfully',
            'id': contact_id
        }), 201

    except Exception as e:
        return jsonify({'error': str(e)}), 500



# Optional: Get all contacts (admin only)
@app.route('/api/admin/contacts', methods=['GET'])
def get_contacts():
    """Get all contact form submissions"""
    try:
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT * FROM contacts ORDER BY created_at DESC')
        contacts = cursor.fetchall()
        cursor.close()

        return jsonify(contacts), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500



# Optional: Update contact status
@app.route('/api/admin/contacts/<int:contact_id>', methods=['PATCH'])
def update_contact_status(contact_id):
    """Update contact status"""
    try:
        data = request.get_json()

        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('''
            UPDATE contacts SET status = %s WHERE id = %s
        ''', (data.get('status', 'new'), contact_id))
        mysql.connection.commit()
        cursor.close()

        return jsonify({'message': 'Contact updated'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500




if __name__ == '__main__':
    app.run(debug=True)
