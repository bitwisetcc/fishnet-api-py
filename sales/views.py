from typing import Any
from bson import Regex
from flask import Blueprint, jsonify, request

from connections import db

sales = Blueprint("sales", __name__)
collection = db["orders_real_users"]


BASE_QUERY = [
    {
        "$lookup": {
            "from": "users",
            "localField": "id_customer",
            "foreignField": "_id",
            "as": "user",
            "pipeline": [
                {"$project": {"name": 1, "cpf": 1}},
                {"$set": {"_id": {"$toString": "$_id"}}},
            ],
        }
    },
    {"$unset": ["id_customer"]},
    {
        "$set": {
            "user": {"$arrayElemAt": ["$user", 0]},
            "items": {
                "$map": {
                    "input": "$items",
                    "as": "item",
                    "in": {
                        "_id": {"$toString": "$$item._id"},
                        "price": {"$toDouble": "$$item.price"},
                        "qty": "$$item.qty",
                    },
                }
            },
            "_id": {"$toString": "$_id"},
            "total": {
                "$sum": {
                    "$map": {"input": "$items", "as": "item", "in": "$$item.price"}
                }
            },
        }
    },
]


@sales.get("/")
def get_all_orders():
    query = collection.aggregate(BASE_QUERY)
    return jsonify(list(query))


@sales.get("/filter")
def filter_sales():
    body = request.get_json()

    filters = []
    ordering = {}
    symbol_mapping = {"+": 1, "-": -1}

    if "username" in body:
        filters.append(
            {
                "$match": {
                    "user.name": {"$regex": Regex(body.username, "i")},
                }
            }
        )

    if "ordering" in body:
        for ord in body["ordering"]:
            key = ord[1:]
            direction = symbol_mapping[ord[0]]

            if key in ["total", "date", "user.name"] and direction in "+-":
                ordering[key] = direction
            else:
                return jsonify({"message": f"Invalid ordering '{ord}'"}), 400

    query = collection.aggregate(BASE_QUERY + filters + {"$order": ordering})

    return jsonify(list(query))
