from math import ceil
from typing import Any

from bson import ObjectId
from flask import Blueprint, jsonify, request

from connections import db
from decorators import bearer_required
from user.models import parse_filters

COLLECTION = db["users"]
users = Blueprint("users", __name__)

# [POST] /users is implemented as /auth/register
# { is_company, name, email, phone, rg*1, cpf*1, cnpj*2, serial_CC, expiration_CC, backserial_CC, zip_code?, address? }


def to_dict(item) -> dict[str, Any]:
    item["_id"] = str(item["_id"])
    del item["password"]
    return item


@users.get("/")
def get_users():
    query = parse_filters(request.args)

    count = int(request.args.get("count", 20))
    page = int(request.args.get("page", 1))
    pagination = [{"$skip": count * (page - 1)}, {"$limit": count}]

    results = COLLECTION.aggregate(query + pagination)

    full_count_result = COLLECTION.aggregate(
        query + [{"$group": {"_id": None, "count": {"$sum": 1}}}],
    )

    full_count = full_count_result.next().get("count", 0)

    if full_count == 0:
        return jsonify({"match": [], "page_count": 0})

    return jsonify(
        {"match": list(map(to_dict, results)), "page_count": ceil(full_count / count)}
    )


@users.get("/<id>")
def get_user_by_id(id):
    user = COLLECTION.find_one({"_id": ObjectId(id)})
    if user:
        return jsonify(to_dict(user)), 200
    return jsonify({"error": "User not found"}), 404


@users.put("/<id>")
def update_user(id):
    final_user = COLLECTION.find_one({"_id": ObjectId(id)})

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

    result = COLLECTION.update_one({"_id": ObjectId(id)}, {"$set": final_user})
    if result.matched_count:
        return jsonify({"message": "User updated"}), 200
    return jsonify({"error": "User not found"}), 404


@users.delete("/<id>")
def delete_user(id):
    result = COLLECTION.delete_one({"_id": ObjectId(id)})
    if result.deleted_count:
        return jsonify({"message": "User deleted"}), 200
    return jsonify({"error": "User not found"}), 404


@users.get("/me")
@bearer_required
def get_user_profile(payload):
    try:
        user = COLLECTION.find_one({"email": payload["email"]})
        user = to_dict(user)
        user.pop("password")
        return jsonify(user), 200
    except Exception as e:
        print(e.args)
        return jsonify(e.args), 500


@users.put("/me")
@bearer_required()
def update_user_profile(payload):
    body = dict(request.get_json())

    blocked_fields = ["email", "name", "_id", "password"]
    filtered = [f for f in blocked_fields if body.get(f, None)]
    if filtered:
        return jsonify(
            {"message": f"Tried to edit blocked fields: {', '.join(filtered)}"}
        )

    res = COLLECTION.update_one({"_id": ObjectId(payload["sub"])}, {"$set": body})
    if not res.acknowledged:
        return jsonify({"message": "Database failed to write data"}), 500

    return jsonify({"message": "Object saved successfully"}), 200
