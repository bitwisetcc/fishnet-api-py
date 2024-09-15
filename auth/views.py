import bcrypt
from flask import current_app, Blueprint, jsonify, request
from flask_cors import cross_origin
import jwt

from connections import db

auth = Blueprint("auth", __name__)
users = db["users"]


@auth.post("/register")
@cross_origin()
def register():
    post_data = request.get_json()

    if users.find_one({"email": post_data.get("email")}) is not None:
        return jsonify({"message": "Usuário já cadastrado."}), 409

    hashed_password = bcrypt.hashpw(
        bytes(post_data.get("password"), "utf-8"), bcrypt.gensalt()
    )

    role = post_data.get("role")
    if role not in ["cpf", "cnpj", "staff"]:
        return jsonify({"message": "Papel inválido."}), 400

    user = {
        "name": post_data.get("name"),
        "email": post_data.get("email"),
        "role": role,
        "password": hashed_password,
    }

    user_id = users.insert_one(user).inserted_id

    payload = {
        "sub": str(user_id),
        "email": user["email"],
        "name": user["name"],
    }

    try:
        auth_token = jwt.encode(payload, current_app.config["SECRET_KEY"])
    except Exception as e:
        print(e.args)
        return jsonify({"message": "Falha ao criar JWT."}), 500

    return jsonify({"token": auth_token}), 201


@auth.post("/login")
@cross_origin()
def login():
    post_data = request.get_json()
    user = users.find_one({"email": post_data.get("email")})

    if user is None:
        return jsonify({"message": "Login inválido."}), 404

    if bcrypt.checkpw(bytes(post_data.get("password"), "utf-8"), user["password"]):
        payload = {
            "sub": str(user["_id"]),
            "email": user["email"],
            "name": user["name"],
        }

        auth_token = jwt.encode(payload, current_app.config["SECRET_KEY"])
        return jsonify({"token": auth_token}), 200
    else:
        return jsonify({"message": "Login inválido."}), 404
