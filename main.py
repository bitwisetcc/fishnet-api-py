from os import environ
from dotenv import load_dotenv
from flask import Flask
from flask_cors import CORS

from auth.views import auth
from dashboard.dash import dashboard
from products.views import products
from sales.views import sales
from user.views import users

# Carregando variáveis de ambiente
load_dotenv()

# Inicializando o aplicativo Flask
app = Flask(__name__)
CORS(app, origins="*")

app.config["CORS_HEADERS"] = "Content-Type"
app.config["SECRET_KEY"] = environ.get("SECRET_KEY", ":^)")

# Registrando blueprints
app.register_blueprint(auth, url_prefix="/auth")
app.register_blueprint(users, url_prefix="/users")
app.register_blueprint(products, url_prefix="/prods")
app.register_blueprint(dashboard, url_prefix="/dash")
app.register_blueprint(sales, url_prefix="/sales")

@app.get("/")
def home():
    return "FishNet API"

if __name__ == "__main__":
    app.run(debug=True)
