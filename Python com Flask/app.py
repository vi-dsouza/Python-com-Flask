from flask import Flask, request, jsonify
from flask_login import UserMixin
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from flask_login import UserMixin, login_user, LoginManager, login_required, logout_user, current_user
app = Flask(__name__)
app.config['SECRET_KEY'] = 'minha_chave123'
#Linha de configuração do nosso banco
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///ecommerce.db'
#Defini uma rota raíz da pagina inicial e a função que sera executada quando o usuário requisitar

login_manager = LoginManager()
#Conexão com o banco
db = SQLAlchemy(app)
login_manager.init_app(app)
login_manager.login_view = 'login'
#Permitir que outros sistemas utilizem a api
CORS(app)

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), nullable=False, unique=True)
    password = db.Column(db.String(80), nullable=False)
    cart = db.relationship('CartItem', backref='user', lazy=True)

#Modelagem - Produto (id, name, price, description)
class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    price = db.Column(db.Float, nullable=False)
    description = db.Column(db.Text, nullable=True)

class CartItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    #Cria uma chave estrangeira para o campo
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)

#Autenticação
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/login', methods=["POST"])
def login():
    data = request.json
    user = User.query.filter_by(username=data.get("username")).first()
    if user:
        if user.password == data.get("password"):
            login_user(user)
            return jsonify({"message": "Login successful!"}), 200
    return jsonify({"message": "Invalid username or password."}), 401

@app.route('/logout', methods=["POST"])
@login_required
def logout():
    logout_user()
    return jsonify({"message": "Logout successful!"}), 200

@app.route('/api/products/add', methods=["POST"])
#Serve para autenticar as rotas e proteger de quem não está autorizado
@login_required
def add_product():
    data = request.json
    if 'name' in data and 'price' in data:
        product = Product(name=data["name"], price=data["price"], description=data.get("description", ""))
        db.session.add(product)
        db.session.commit()
        return jsonify({"message": "Product added successfully!"}), 200
    return jsonify({'message': "Invaled product data."}), 400

@app.route('/api/products/delete/<int:product_id>', methods=["DELETE"])
#Serve para autenticar as rotas e proteger de quem não está autorizado
@login_required
def delete_product(product_id):
    #Recuperar o produto da nossa base de dados
    #Verificar se ele existe
    # Se existe, apagar da basse de dados
    # Se nao existe, retornar 404 not found
    product = Product.query.get(product_id)
    if product:
        db.session.delete(product)
        db.session.commit()
        return jsonify({"message": "Product deleted successfully!"}), 200
    return jsonify({"message": "Product not found."}), 404

@app.route('/api/product/<int:product_id>', methods=["GET"])
def get_product_details(product_id):
    product = Product.query.get(product_id)
    if product:
        return jsonify({"id": product_id,
                        "name": product.name,
                        "price": product.price,
                        "description": product.description
                        }), 200
    return jsonify({"message": "Product not found."}), 404

@app.route('/api/products/update/<int:product_id>', methods=["PUT"])
#Serve para autenticar as rotas e proteger de quem não está autorizado
@login_required
def update_products(product_id):
    product = Product.query.get(product_id)
    if not product:
        return jsonify({"message": "Product not found."}), 404

    data = request.json
    if 'name' in data:
        product.name = data["name"]

    if 'price' in data:
        product.price = data["price"]

    if 'description' in data:
        product.description = data["description"]

    db.session.commit()
    return jsonify({"message": "Product updated successfully!"}), 200

@app.route('/api/products', methods=["GET"])
def get_all_products():
    products= Product.query.all()
    product_list = []
    for product in products:
        product_data = {
            "id": product.id,
            "name": product.name,
            "price": product.price
        }
        product_list.append(product_data)
    return jsonify(product_list), 200

#Checkout
@app.route('/api/cart/add/<int:product_id>', methods=['POST'])
@login_required
def add_to_cart(product_id):
    #Recuperar usuário
    user = User.query.get(int(current_user.id))
    #Produto
    product = Product.query.get(product_id)

    #Seu eu tiver o usuário e o produto
    if user and product:
        #Criando uma instancia do cart item
        cart_item = CartItem(user_id=user.id, product_id=product.id)
        db.session.add(cart_item)
        db.session.commit()
        return jsonify({"message": "Item add to the cart successfully"}), 200
    return jsonify({"message": "Failed to add item to the cart"}), 400

@app.route('/api/cart/remove/<int:product_id>', methods=['DELETE'])
@login_required
def remove_from_cart(product_id):
    #Porcurar o item no carrinho direto com as duas informacoes que ja tenho
    cart_item = CartItem.query.filter_by(user_id=current_user.id, product_id=product_id).first()
    if cart_item:
        db.session.delete(cart_item)
        db.session.commit()
        return jsonify({"message": "Item removed from the cart"}), 200
    return jsonify({"message": "Failed to remove item from the cart"}), 400

@app.route('/api/cart', methods=['GET'])
@login_required
def view_cart():
    #Usario
    user = User.query.get(int(current_user.id))
    cart_items = user.cart
    cart_content = []
    for cart_item in cart_items:
        #Nao tem uma performance muito boa
        product = Product.query.get(cart_item.product_id)
        cart_content.append({
            "id": cart_item.id,
            "user_id": cart_item.user_id,
            "product_id": cart_item.product_id,
            "product_name": product.name,
            "product_price": product.price,
        })
    return jsonify(cart_content), 200

@app.route('/api/cart/checkout', methods=['POST'])
@login_required
def checkout():
    user = User.query.get(int(current_user.id))
    cart_items = user.cart
    for cart_item in cart_items:
        db.session.delete(cart_item)
    db.session.commit()
    return jsonify({"message": "Checkout successful. Cart has been clared."}), 200

if __name__ == "__main__":
    #Tornar a api disponível (Não usar quando for pra produção)
    app.run(debug=True)