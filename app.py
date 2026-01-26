from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_mysqldb import MySQL
from flask_cors import CORS
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import os
import MySQLdb.cursors
from dotenv import load_dotenv
import secrets
import threading
import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from flask import send_from_directory
from werkzeug.utils import secure_filename
import requests
import random 
from imagekitio import ImageKit
from dotenv import load_dotenv
import traceback
import os





load_dotenv()

app = Flask(__name__)
CORS(app)
METAL_API_URL = "https://api.metalpriceapi.com/v1/latest"
API_KEY = os.getenv("GOLD_API_KEY")

app.config['MYSQL_HOST'] = os.getenv('MYSQL_HOST')
app.config['MYSQL_USER'] = os.getenv('MYSQL_USER')
app.config['MYSQL_PASSWORD'] = os.getenv('MYSQL_PASSWORD')
app.config['MYSQL_DB'] = os.getenv('MYSQL_DB')
app.config['MYSQL_PORT'] = int(os.getenv('MYSQL_PORT'))

app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET_KEY')
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
app.config['APP_URL'] = os.getenv('APP_URL')
app.config['API_KEY'] = os.getenv('API_KEY')
app.config['API_SECRET'] = os.getenv('API_SECRET')


IMAGEKIT_PUBLIC_KEY = os.getenv("IMAGEKIT_PUBLIC_KEY")
IMAGEKIT_PRIVATE_KEY = os.getenv("IMAGEKIT_PRIVATE_KEY")
IMAGEKIT_URL_ENDPOINT = os.getenv("IMAGEKIT_URL_ENDPOINT")

jwt = JWTManager(app)



app.config['fir_tech']=os.getenv('SENDER')
app.config['sec_tech']=os.getenv('PASSWORD')


#LOG FILE
log_filename = "script.log"
logging.basicConfig(
    filename=log_filename,
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s: %(message)s",
)

mysql=MySQL(app)

# DATABSE CONNECTION
def get_db_cursor(dictionary=False):
    """Return MySQL cursor"""
    if dictionary:
        return mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    return mysql.connection.cursor()

# TEST DATABASE
@app.route('/testdb')
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
    data={"message":"welcome to Jewell_shop "}
    return jsonify(data),200
    
    
@app.route('/protected', methods=['GET'])
@jwt_required()
def protected():
    current_user = get_jwt_identity()
    print(current_user)
    return jsonify(logged_in_as=current_user)

# SEND EMAIL 
def send_email(to_email, subject, body):
    try:
        sender_email = app.config['fir_tech']
        sender_password = app.config['sec_tech']

        msg = MIMEMultipart()
        msg['From'] = sender_email
        msg['To'] = to_email
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))

        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(sender_email, sender_password)
        server.sendmail(sender_email, to_email, msg.as_string())
        server.quit()

        return True
    except Exception as e:
        logging.error(f"Email sending failed: {str(e)}")
        return False

# WELCOME MAIL
def send_welcome_email(app, receiver_email):
    try:
        sender_email = app.config['fir_tech']
        sender_password = app.config['sec_tech']
        subject = "Warm Welcome from Shirish and it's team side"

        msg = MIMEMultipart()
        msg['From'] = sender_email
        msg['To'] = receiver_email
        msg['Subject'] = subject

        body = """Hi,

My name is Shirish, I am the CEO of hekratech.pvt.lim.
This is an automated email, but if you reply it will go straight to me.

If you have any feedback or comments on our product I would love to hear it.
If you are considering using this website, please get in touch.
We would be happy to assist you.

Thanks,
Shirish Dwivedi
"""
        msg.attach(MIMEText(body, 'plain'))

        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(sender_email, sender_password)
        server.sendmail(sender_email, receiver_email, msg.as_string())
        server.quit()

        logging.info("Welcome email sent successfully")

    except Exception as e:
        logging.error(f"Email sending failed: {str(e)}")

# REGISTER    
@app.route('/register', methods=['POST'])
def register():
    try:
        data = request.get_json()

        username = data.get('username')
        email = data.get('email')
        password = data.get('password')
        user_id = data.get('user_id') or username

        if not username or not email or not password:
            return jsonify({"error": "All fields are required"}), 400

        # Check existing user
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

        # Insert user
        cursor = get_db_cursor()
        cursor.execute(
            """INSERT INTO users 
               (user_id, username, password, org_password, email, role) 
               VALUES (%s,%s,%s,%s,%s,%s)""",
            (user_id, username, hashed_password, password, email, 'user')
        )
        mysql.connection.commit()
        cursor.close()

        logging.info(f"New user registered: {username}")

        # START EMAIL THREAD (NON-BLOCKING)
        email_thread = threading.Thread(
            target=send_welcome_email,
            args=(app, email),
            daemon=True
        )
        email_thread.start()

        # Create JWT
        access_token = create_access_token(identity=user_id)

        #  IMMEDIATE RESPONSE TO UI
        return jsonify({
            "message": "User registered successfully",
            "access_token": access_token,
            "user": {
                "user_id": user_id,
                "username": username,
                "email": email,
                "role": "user"
            }
        }), 201

    except Exception as e:
        logging.error(str(e))
        return jsonify({
            "message": "Registration failed",
            "error": str(e)
        }), 500


#LOGIN
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

    if email.strip()=="admin123@gmail.com":
        cursor=get_db_cursor(dictionary=True)
        cursor.execute("update users set role='admin' where email=%s",(email,))
        mysql.connection.commit()
        cursor.close()
         
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
                "email": user['email'],
                "role":user['role']
            }
        }), 200

    return jsonify({"msg": "Invalid email or password"}), 401


#FORGET PASSWORD
@app.route('/forgetpassword', methods=['POST'])
def forget_password():
    try:
        # Step 1: Get JSON data
        try:
            data = request.get_json()
            if not data or 'email' not in data:
                logging.warning("Email not provided in request")
                return jsonify({"msg": "email is required"}), 400
            email = data['email'].strip().lower()
            logging.info("Received email: %s", email)
        except Exception as e:
            logging.exception("Error parsing JSON")
            return jsonify({"msg": "invalid request format"}), 400

        # Step 2: Get DB cursor
        try:
            cursor = get_db_cursor(dictionary=True)
            if not cursor:
                logging.error("Database cursor not created")
                return jsonify({"msg": "DB error"}), 500
        except Exception as e:
            logging.exception("DB connection failed")
            return jsonify({"msg": "DB connection failed"}), 500

        # Step 3: Check if user exists
        try:
            cursor.execute("SELECT user_id FROM users WHERE LOWER(email)=%s", (email,))
            user = cursor.fetchone()
            if not user:
                logging.info("User not found: %s", email)
                cursor.close()
                return jsonify({"msg": "user not exists"}), 404
        except Exception as e:
            logging.exception("Error querying user")
            cursor.close()
            return jsonify({"msg": "DB query error"}), 500

        # Step 4: Generate reset token
        try:
            reset_token = secrets.token_urlsafe(32)
            expiry_time = datetime.utcnow() + timedelta(minutes=15)
            logging.info("Generated reset token for: %s", email)
        except Exception as e:
            logging.exception("Error generating reset token")
            return jsonify({"msg": "token generation error"}), 500

        # Step 5: Update user with token
        try:
            cursor.execute(
                "UPDATE users SET reset_token=%s, reset_token_expiry=%s WHERE email=%s",
                (reset_token, expiry_time, email)
            )
            cursor.connection.commit()
            cursor.close()
        except Exception as e:
            logging.exception("Error updating user reset token")
            cursor.close()
            return jsonify({"msg": "DB update error"}), 500

        # Step 6: Send email
        try:
            reset_link = f"https://696514e00b2ec20c00c27df1--hridikajewellers.netlify.app/reset-password?token={reset_token}"


            subject = "Reset Your Password"
            body = f"Hi,\n\nClick to reset your password: {reset_link}\nLink valid for 15 minutes."
            send_email(email, subject, body)
            logging.info("Reset email sent to: %s", email)
        except Exception as e:
            logging.exception("Failed to send reset email")
            return jsonify({"msg": "Failed to send email"}), 500

        return jsonify({"msg": "Reset password link sent to your email","token":reset_token}), 200

    except Exception as e:
        logging.exception("Unhandled forget password error")
        return jsonify({"msg": "internal server error"}), 500

#RESET PASSOWRD
@app.route('/resetpassword', methods=['POST'])
def reset_password():
    try:
        data = request.get_json()
        token = data.get('token')
        new_password = data.get('password')
        #confirm_password = data.get

        if not token or not new_password:
            return jsonify({"msg": "token and new_password required"}), 400

        cursor = get_db_cursor(dictionary=True)
        cursor.execute(
            """
            SELECT user_id FROM users 
            WHERE reset_token=%s 
            AND reset_token_expiry > UTC_TIMESTAMP()
            """,
            (token,)
        )
        user = cursor.fetchone()
        logging.info(user)
        if not user:
            cursor.close()
            return jsonify({"msg": "Invalid or expired token"}), 400

        hashed_password = generate_password_hash(new_password)

        cursor.execute(
            """
            UPDATE users 
            SET password=%s, org_password=%s, reset_token=NULL, reset_token_expiry=NULL
            WHERE user_id=%s
            """,
            (hashed_password, new_password, user['user_id'])
        )
        cursor.connection.commit()
        cursor.close()

        return jsonify({"msg": "Password reset successful"}), 200

    except Exception:
        logging.exception("Reset password error")
        return jsonify({"msg": "internal server error"}), 500

# GET ALL USERS 
@app.route('/api/admin/users', methods=['GET'])
@jwt_required()
def get_all_users():
    cursor = get_db_cursor(dictionary=True)
    cursor.execute("SELECT user_id, username, email , Phone FROM users")
    users = cursor.fetchall()
    cursor.close()
    return jsonify(users), 200



#CONVERSION TO BASE64 TO IMAGEKIT URL
def upload_base64_to_imagekit(base64_image):
    response = requests.post(
        "https://upload.imagekit.io/api/v1/files/upload",
        auth=(IMAGEKIT_PRIVATE_KEY, ""),   # Basic Auth
        data={
            "file": base64_image,          # data:image/...;base64,...
            "fileName": "product.jpg",
            "folder": "/products"
        }
    )

    if response.status_code != 200:
        raise Exception(response.text)

    return response.json()["url"]

# ADD PRODUCT
@app.route('/products', methods=['POST'])
@jwt_required()
def create_product():
    """
    Admin only
    Fields: name, category, price, description, stock, images
    """
    try:
        data = request.get_json()
        base64_image = data.get("images")
        image_url = None
        
        logging.info(base64_image)
        
        if base64_image:
            image_url = upload_base64_to_imagekit(base64_image)
        logging.info(image_url)
        logging.info(base64_image)
        try:
            cursor = get_db_cursor()
            cursor.execute("""
                INSERT INTO products (name, category, price, description, stock, images, quantity, metal_name)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
            """, (
                data['name'],
                data.get('category'),
                data.get('price'),
                data.get('description'),
                data.get('stock'),
                image_url,
                data.get('quantity'),
                data.get('metal_name')
            )
            )
            mysql.connection.commit()
            cursor.close()
            return jsonify({"msg": "Product created successfully",
            "image_url": image_url}), 201 
        except Exception as e:
            logging.info("Hello",str(e))
            return jsonify({"msg":"Product not created","error":str(e)}), 401 
    except Exception as e:
        logging.info("Hello",str(e))
        return jsonify({"msg":"Product not created","error":str(e)}), 401 

# GET ALL PRODUCT
@app.route('/products', methods=['GET'])
def get_products():
    """
    Get all products
    """
    try:
        cursor = get_db_cursor()
        cursor.execute("SELECT id, name, category, description, stock, images , quantity FROM products")
        products = cursor.fetchall()
        cursor.close()
    except Exception as e:
        return jsonify({"error":str(e)}),500
    
    logging.info(products)
    print(products)
    result = [
        {"id": p[0], "name": p[1], "category": p[2], 
         "description": p[3], "stock": p[4], "images": p[5],"quantity":p[6] } for p in products
    ]
    return jsonify(result), 200

# DELETE THE PRODUCT
@app.route("/products/<int:id>", methods=["DELETE"])
@jwt_required()
def delete_product(id):
    cursor = get_db_cursor()
    cursor.execute("DELETE FROM products WHERE id=%s", (id,))
    mysql.connection.commit()
    cursor.close()
    return jsonify({"message": "Product deleted"})

# UPDATE PRODUCT
@app.route("/products/<int:id>", methods=["PUT"])
@jwt_required()
def update_product(id):
    try:
        data = request.get_json()
        cursor = get_db_cursor(dictionary=True)

        cursor.execute("SELECT * FROM products WHERE id=%s", (id,))
        product = cursor.fetchone()

        if not product:
            return jsonify({"msg": "Product not found"}), 404
        
        image_url = product["images"]
        new_base64 = data.get("images")
        if new_base64:
            image_url = upload_base64_to_imagekit(new_base64)

        cursor.execute("""
            UPDATE products SET
            name=%s,
            category=%s,
            description=%s,
            stock=%s,
            quantity=%s,
            metal_name=%s,
            images=%s,
            price=%s
            WHERE id=%s
        """, (
            data.get("name", product["name"]),
            data.get("category", product["category"]),
            data.get("description", product["description"]),
            int(data.get("stock", product["stock"])),
            data.get("quantity", product["quantity"]),
            data.get("metal_name") or product["metal_name"] or "Gold",
            image_url,
            float(data.get("price", product["price"])),
            id
        ))

        mysql.connection.commit()
        cursor.close()
        return jsonify({"msg": "Product updated successfully"}), 200

    except Exception as e:
        print("UPDATE ERROR =", e)
        return jsonify({"error": str(e)}), 500

# GET PRODUCT BY ID
@app.route('/products/<int:id>', methods=['GET'])
def get_product(id):
    """
    Get product by id
    """
    cursor = get_db_cursor()
    cursor.execute("SELECT id, name, category, price, description, stock, images , quantity FROM products WHERE id=%s", (id,))
    product = cursor.fetchone()
    cursor.close()

    if product:
        return jsonify({
            "id": product[0], "name": product[1], "category": product[2],
            "price": product[3], "description": product[4], "stock": product[5],
            "images": product[6] , "quantity":product[7]
        }), 200
    return jsonify({"message": "Product not found"}), 404


@app.route('/profile', methods=['GET'])
@jwt_required()
def profile():
    user_id = get_jwt_identity()
    return jsonify({"user_id": user_id}), 200

# ADD TO CART
@app.route('/cart', methods=['POST'])
@jwt_required()
def add_to_cart():
    user_id = get_jwt_identity()
    data = request.get_json()

    product_id = data.get("product_id")  
    quantity = data.get("quantity", 1)  

    cursor = get_db_cursor()  

    cursor.execute(
        "SELECT quantity FROM cart WHERE user_id=%s AND product_id=%s",
        (user_id, product_id)
    )
    existing = cursor.fetchone()

    if existing:
        cursor.execute(
            "UPDATE cart SET quantity=quantity+%s WHERE user_id=%s AND product_id=%s",
            (1, user_id, product_id)
        )
    else:
        cursor.execute(
            "INSERT INTO cart (user_id, product_id, quantity) VALUES (%s,%s,%s)",
            (user_id, product_id, 1)
        )

    mysql.connection.commit()
    cursor.close()

    return jsonify({"msg": "Product added to cart", "quantity": quantity}), 201


# GET CART
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

# UPDATE CART
@app.route('/cart/update', methods=['PUT'])
@jwt_required()
def update_cart_quantity():
    """
    Update cart item quantity (minimum 10)
    """
    user_id = get_jwt_identity()
    data = request.get_json()

    product_id = data.get('product_id')
    quantity = data.get('quantity')

    if not product_id or not quantity:
        return jsonify({"msg": "Product ID and quantity required"}), 400

    # if quantity < 10:
    #     return jsonify({"msg": "Minimum quantity is 10"}), 400
    
    logging.info(data)
    cursor = get_db_cursor()
    cursor.execute(
        "UPDATE cart SET quantity=quantity+%s WHERE user_id=%s AND product_id=%s",
        (1, user_id, product_id)
    )

    mysql.connection.commit()
    cursor.close()

    return jsonify({"msg": "Quantity updated successfully"}), 200

# UPDATE CART QUATNTITY MIN 10
@app.route('/cart/update/min', methods=['PUT'])
@jwt_required()
def update_cart_quantity_min():
    """
    Update cart item quantity (minimum 10)
    """
    user_id = get_jwt_identity()
    data = request.get_json()

    product_id = data.get('product_id')
    quantity = data.get('quantity')

    if not product_id or not quantity:
        return jsonify({"msg": "Product ID and quantity required"}), 400

    logging.info(data)
    cursor = get_db_cursor()
    cursor.execute(
        "UPDATE cart SET quantity=quantity-%s WHERE user_id=%s AND product_id=%s",
        (1, user_id, product_id)
    )

    mysql.connection.commit()
    cursor.close()

    return jsonify({"msg": "Quantity updated successfully"}), 200

# DELETE FROM CART
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


# CREATE ORDER
@app.route('/orders', methods=['POST'])
@jwt_required()
def create_order():
    """
    Create order from cart
    Fields: address, payment_method
    """
    user_id = get_jwt_identity()
    data = request.get_json()
    logging.info(data)
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

# GET ALL ORDERS FOR ADMIN
@app.route('/api/admin/orders',methods=['GET'])
@jwt_required()
def get_orders_admin():
    """
    Get all orders for a ADMIN
    """
    user_id = get_jwt_identity()
    cursor = get_db_cursor()
    cursor.execute("SELECT id, address, payment_method, status, created_at FROM orders ")
    orders = cursor.fetchall()
    cursor.close()

    result = [{"id": o[0], "address": o[1], "payment_method": o[2], "status": o[3], "created_at": str(o[4])} for o in orders]
    return jsonify(result), 200


# GET ALL ORDERS FOR USER
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

#UPDATE ORDER STATUS
@app.route('/api/admin/orders/<int:order_id>', methods=['PUT'])
@jwt_required()
def update_order_status(order_id):
    data = request.get_json()
    cursor = get_db_cursor()
    cursor.execute(
        "UPDATE orders SET status=%s WHERE id=%s",
        (data['status'], order_id)
    )
    mysql.connection.commit()
    cursor.close()
    return jsonify({"msg": "Order updated"}), 200


#GET ALL CATEGORY
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

#GET ALL PRODUCT BY CATEGORY
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


# SEND MAIL
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
        
        

#SUBMIT CONTACT
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

#UPDATE CONTACT STATUS
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

#SAVE BESPOKE QUERY
@app.route("/api/bespoke-request", methods=["POST"])
@jwt_required()
def save_bespoke():
    try:
        name = request.form.get("name")
        phone = request.form.get("phone")
        product = request.form.get("product")
        details = request.form.get("details")
        size = request.form.get("size")
        image = request.files.get("image")
        image_url = None

        if image:
            # 👇 ImageKit direct upload (file object)
            response = requests.post(
                "https://upload.imagekit.io/api/v1/files/upload",
                auth=(IMAGEKIT_PRIVATE_KEY, ""),
                files={
                    "file": image
                },
                data={
                    "fileName": image.filename,
                    "folder": "/bespoke"
                }
            )

            if response.status_code != 200:
                raise Exception(response.text)

            image_url = response.json()["url"]

        cursor = mysql.connection.cursor()
        cursor.execute("""
            INSERT INTO bespoke_requests
            (full_name, phone, product_type, design_details, size, image_url)
            VALUES (%s,%s,%s,%s,%s,%s)
        """, (name, phone, product, details, size, image_url))

        mysql.connection.commit()
        cursor.close()

        return jsonify({"msg": "Bespoke request submitted"}), 201

    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
 #GET ALL BESPOKE QUERY   
@app.route("/api/bespoke-requests", methods=["GET","OPTIONS"])
def get_bespoke_requests():
    try:
        if request.method == "OPTIONS":
            return "", 200
        
        cursor = get_db_cursor(dictionary=True)

        cursor.execute("""
            SELECT
              id,
              full_name,
              phone,
              product_type,
              design_details,
              size,
              image_url,
              created_at
            FROM bespoke_requests
            ORDER BY created_at DESC
        """)
        data = cursor.fetchall()
        cursor.close()

        return jsonify(data), 200

    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route("/auth/send-otp", methods=["POST"])
def send_otp():
    data = request.get_json()
    phone = data.get("phone")

    if not phone:
        return jsonify({"msg": "Phone number required"}), 400

    payload = {
        "mobile": phone,
        "authkey": os.getenv("MSG91_AUTH_KEY"),
        "otp_length": 6,
        "otp_expiry": 5
    }

    response = requests.post(
        "https://control.msg91.com/api/v5/otp",
        json=payload
    )
    try:
        return jsonify(response.json()), response.status_code
    except:
        return jsonify({"msg": "OTP sent"}), 200

@app.route("/auth/verify-otp", methods=["POST"])
def verify_otp():
    data = request.get_json()
    phone = data.get("phone")
    name = data.get("name")
    otp = data.get("otp")

    if not phone or not otp:
        return jsonify({"msg": "Phone and OTP required"}), 400

    # Verify OTP from MSG91
    payload = {
        "mobile": phone,
        "otp": otp,
        "authkey": os.getenv("MSG91_AUTH_KEY")
    }

    res = requests.post(
        "https://control.msg91.com/api/v5/otp/verify",
        json=payload
    )

    result = res.json()
    if result.get("type") != "success":
        return jsonify({"msg": "Invalid OTP"}), 401

    cursor = get_db_cursor(dictionary=True)
    cursor.execute("SELECT * FROM otp_user WHERE phone=%s", (phone,))
    user = cursor.fetchone()

    if not user:
        cursor.execute("""
            INSERT INTO otp_user (name, phone, is_verified)
            VALUES (%s,%s,1)
        """, (name, phone))
        mysql.connection.commit()

    cursor.close()

    token = create_access_token(identity={
        "phone": phone,
        "role": "user",
        "auth_type": "otp"
    })

    return jsonify({
        "access_token": token,
        "msg": "Login successful",
    }), 200



# MAIN METHOD
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))