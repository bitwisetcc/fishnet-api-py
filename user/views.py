from bson import ObjectId
from flask import Blueprint, jsonify, request
from flask_pydantic import validate

from connections import db

collection = db["users"]
users = Blueprint("users", __name__)

# [POST] /users is not here because it is implemented in auth/views.py as /auth/register


def to_dict(item):
    return {**item, "_id": str(item["_id"]), "password": item["password"].decode()}


@users.get("/")
def get_users():
    user = list(collection.find())
    return jsonify([to_dict(e) for e in user]), 200


@users.get("/<id>")
def get_user_by_id(id):
    user = collection.find_one({"_id": ObjectId(id)})
    if user:
        return jsonify(to_dict(user)), 200
    return jsonify({"error": "User not found"}), 404


@users.put("/<id>")
@validate()
def update_user(id):
    updated_user = request.json
    result = collection.update_one({"_id": ObjectId(id)}, {"$set": updated_user})
    if result.matched_count:
        return jsonify({"message": "User updated"}), 200
    return jsonify({"error": "User not found"}), 404


@users.delete("/<id>")
def delete_user(id):
    result = collection.delete_one({"_id": ObjectId(id)})
    if result.deleted_count:
        return jsonify({"message": "User deleted"}), 200
    return jsonify({"error": "User not found"}), 404
