from flask import Blueprint, jsonify, request

from connections import db

sales = Blueprint("sales", __name__)
collection = db["orders_real_users"]


def to_dict(item):
    item["_id"] = str(item["_id"])
    item["user"]["_id"] = str(item["user"]["_id"])
    for item in item["items"]:
        item["_id"] = str()
    return item


@sales.get("/")
def get_all_orders():
    query = collection.aggregate(
        [
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
                }
            },
        ]
    )

    return jsonify(list(query))
