from bson import ObjectId
from flask import Blueprint, jsonify, request
from flask_pydantic import validate

from connections import db

collection = db["users"]
users = Blueprint("users", __name__)

# [POST] /users is implemented as /auth/register
# { is_company, name, email, phone, rg*1, cpf*1, cnpj*2, serial_CC, expiration_CC, backserial_CC, zip_code?, address? }


def to_dict(item):
    item["_id"] = str(item["_id"])
    item["password"] = item["password"].decode()
    return item


@users.get("/")
def get_users():
    users = list(collection.find())
    return jsonify([to_dict(e) for e in users]), 200


@users.get("/role/<role>")
def get_users_by_role(role):
    users = list(collection.find({"role": role}))
    return jsonify([to_dict(e) for e in users]), 200


@users.get("/<id>")
def get_user_by_id(id):
    user = collection.find_one({"_id": ObjectId(id)})
    if user:
        return jsonify(to_dict(user)), 200
    return jsonify({"error": "User not found"}), 404


@users.put("/<id>")
@validate()
def update_user(id):
    final_user = collection.find_one({"_id": ObjectId(id)})

    if final_user is None:
        return jsonify({"error": "User not found"}), 404

    for key, value in request.json.items():
        if key not in ["_id", "email", "password"]:
            if key == "role" and value not in ["cpf", "cnpj", "staff"]:
                return jsonify({"error": "Invalid role"}), 400

            final_user[key] = value
        else:
            return (
                jsonify(
                    {"error": "Trying to update locked fields: id, email or password"}
                ),
                400,
            )

    result = collection.update_one({"_id": ObjectId(id)}, {"$set": final_user})
    if result.matched_count:
        return jsonify({"message": "User updated"}), 200
    return jsonify({"error": "User not found"}), 404


@users.delete("/<id>")
def delete_user(id):
    result = collection.delete_one({"_id": ObjectId(id)})
    if result.deleted_count:
        return jsonify({"message": "User deleted"}), 200
    return jsonify({"error": "User not found"}), 404
