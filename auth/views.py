from functools import wraps

import bcrypt
import jwt
from bson import ObjectId
from flask import Blueprint, current_app, jsonify, request
from flask_cors import cross_origin

from connections import db

auth = Blueprint("auth", __name__)
users = db["users"]


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        auth_header = request.headers.get("Authorization")

        if auth_header is None:
            return jsonify({"message": "Token não fornecido."}), 400

        try:
            payload = jwt.decode(
                auth_header.encode(),
                current_app.config["SECRET_KEY"],
                algorithms=["HS256"],
            )
        except Exception as e:
            print(e.args)
            return jsonify({"message": "Token inválido."}), 400

        user = users.find_one({"_id": ObjectId(payload["sub"])})
        if user is None:
            return jsonify({"message": "Usuário não encontrado.", "res": payload}), 404

        return f(*args, payload, **kwargs)

    return decorated_function


@auth.post("/register")
@cross_origin()
def register():
    post_data = request.get_json()

    if not all(
        [post_data.get("name"), post_data.get("email"), post_data.get("password")]
    ):
        return jsonify({"message": "Dados inválidos."}), 415

    if users.find_one({"email": post_data.get("email")}) is not None:
        return jsonify({"message": "Usuário já cadastrado."}), 409

    hashed_password = bcrypt.hashpw(
        post_data.get("password").encode(), bcrypt.gensalt()
    )

    role = post_data.get("role")
    if role not in ["admin", "cpf", "cnpj", "staff"]:
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
    if post_data.get("email") is None or post_data.get("password") is None:
        return jsonify({"message": "Dados inválidos."}), 415

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

    return jsonify({"message": "Login inválido."}), 404


@auth.get("/check")
@cross_origin()
def me():
    auth_header = request.headers.get("Authorization")
    if auth_header is None:
        return jsonify({"message": "Token não fornecido."}), 400

    try:
        payload = jwt.decode(
            auth_header.encode(), current_app.config["SECRET_KEY"], algorithms=["HS256"]
        )
    except Exception as e:
        print(e.args)
        return jsonify({"message": "Token inválido."}), 400

    user = users.find_one({"_id": ObjectId(payload["sub"])})
    if user is None:
        return jsonify({"message": "Usuário não encontrado.", "res": payload}), 404

    return (
        jsonify(
            {
                "name": user["name"],
                "email": user["email"],
                "picture": user.get(
                    "picture", "https://avatars.githubusercontent.com/u/8683378"
                ),
            }
        ),
        200,
    )


@auth.post("/password")
@login_required
@cross_origin()
def change_password(payload):
    post_data = request.get_json()
    # user = users.find_one({"_id": ObjectId(post_data.get("id"))})
    user = users.find_one({"_id": ObjectId(payload["sub"])})

    if user is None:
        return jsonify({"message": "Usuário não encontrado."}), 404

    if bcrypt.checkpw(post_data.get("old_password").encode(), user["password"]):
        hashed_password = bcrypt.hashpw(
            post_data.get("new_password").encode(), bcrypt.gensalt()
        )

        users.update_one(
            {"_id": ObjectId(payload["sub"])},
            {"$set": {"password": hashed_password}},
        )
        return jsonify({"message": "Senha alterada com sucesso."}), 200

    return jsonify({"message": "Senha antiga inválida."}), 400


# @auth.post("/reset-psasword")
# @cross_origin()
# def reset_password():
#     post_data = request.get_json()
#     user = users.find_one({"email": post_data.get("email")})

#     if user is None:
#         return jsonify({"message": "Usuário não encontrado."}), 404

#     hashed_password = bcrypt.hashpw(
#         post_data.get("password").encode(), bcrypt.gensalt()
#     )

#     users.update_one({"email": post_data.get("email")}, {"$set": {"password": hashed_password}})
#     return jsonify({"message": "Senha alterada com sucesso."}), 200
