from os import environ

from dotenv import load_dotenv
from flask import Flask
from flask_cors import CORS

from connections import db
from auth.views import auth
from products.views import products
from user.views import users

species = db["species"]
customers = db["customers"]

load_dotenv()

app = Flask(__name__)
cors = CORS(app)
app.config["CORS_HEADERS"] = "Content-Type"
app.config["SECRET_KEY"] = environ.get("SECRET_KEY", ":^)")

app.register_blueprint(auth, url_prefix="/auth")
app.register_blueprint(users, url_prefix="/users")
app.register_blueprint(products, url_prefix="/prods")


if __name__ == "__main__":
    app.run(debug=True)
