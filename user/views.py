from collections import defaultdict
from math import ceil
from typing import Any
from bson import ObjectId, Regex
from flask import Blueprint, jsonify, request
import pymongo

from auth.views import login_required
from connections import db

COLLECTION = db["users"]
users = Blueprint("users", __name__)

# [POST] /users is implemented as /auth/register
# { is_company, name, email, phone, rg*1, cpf*1, cnpj*2, serial_CC, expiration_CC, backserial_CC, zip_code?, address? }


def to_dict(item) -> dict[str, Any]:
    item["_id"] = str(item["_id"])
    item["password"] = item["password"].decode()
    return item


@users.get("/")
def get_users():
    users = list(COLLECTION.find())
    return jsonify([to_dict(e) for e in users]), 200


@users.get("/role/<role>")
def get_users_by_role(role):
    users = list(COLLECTION.find({"role": role}))
    return jsonify([to_dict(e) for e in users]), 200


@users.get("/filter")
def filter_users():
    body = request.args

    filters = defaultdict(dict)
    ordering = {}

    if "name" in body:
        filters["name"] = {"$regex": Regex(body["name"], "i")}

    if "email" in body:
        filters["email"] = {"$regex": Regex(body["email"])}

    if "tel" in body:
        filters["tel"] = {"$regex": Regex(rf"\b{body["tel"]}\d*")}

    if "role" in body:
        filters["role"] = "role"

    if "ordering" in body:
        symbol_mapping = {"+": pymongo.ASCENDING, "-": pymongo.DESCENDING}
        for ord in body["ordering"].split(","):
            key = ord[1:]
            direction = symbol_mapping.get(ord[0])

            if key in ["name", "tel", "email", "addr", "uf"] and direction is not None:
                ordering[key] = direction
            else:
                return jsonify({"message": f"Invalid ordering '{ord}'"}), 400

    if not ordering:
        ordering["_id"] = pymongo.ASCENDING

    count = int(body.get("count", 20))
    page = int(body.get("page", 1))
    pagination = [{"$skip": count * (page - 1)}, {"$limit": count}]

    query = COLLECTION.aggregate(
        [{"$match": filters}, {"$sort": ordering}] + pagination
    )

    full_count_result = COLLECTION.aggregate(
        [
            {"$match": filters},
            {"$sort": ordering},
            {"$group": {"_id": None, "count": {"$sum": 1}}},
        ]
    )

    full_count = 0
    for result in full_count_result:
        full_count = result.get("count", 0)

    if full_count == 0:
        return jsonify({"match": [], "page_count": 0})

    return jsonify({"match": list(query), "page_count": ceil(full_count / count)})


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
@login_required
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
@login_required
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
