from collections import defaultdict
from datetime import datetime
from math import ceil

from bson import Regex
from flask import Blueprint, jsonify, request
import pymongo

from connections import db
from sales.validation import Sale

sales = Blueprint("sales", __name__)
COLLECTION = db["orders"]
CUSTOMERS = db["users"]


BASE_QUERY = [
    {
        "$lookup": {
            "from": "users",
            "localField": "customer_id",
            "foreignField": "_id",
            "as": "user",
            "pipeline": [
                {"$project": {"name": 1}},
                {"$set": {"_id": {"$toString": "$_id"}}},
            ],
        }
    },
    {"$unset": ["customer_id"]},
    {
        "$set": {
            "temp": "$customer",
            "customer": {"$arrayElemAt": ["$user", 0]},
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
            "tax": {"$toDouble": "$tax"},
            "shipping": {"$toDouble": "$shipping"},
            "_id": {"$toString": "$_id"},
            "total": {
                "$toDouble": {
                    "$sum": [
                        {
                            "$sum": {
                                "$map": {
                                    "input": "$items",
                                    "as": "item",
                                    "in": {"$multiply": ["$$item.price", "$$item.qty"]},
                                }
                            }
                        },
                        {"$toDouble": "$tax"},
                        {"$toDouble": "$shipping"},
                    ]
                }
            },
        }
    },
    {"$set": {"customer": {"$ifNull": ["$customer", "$temp", "$customer"]}}},
    {"$unset": ["temp", "user"]},
]


@sales.get("/")
def get_all_orders():
    query = COLLECTION.aggregate(BASE_QUERY)
    return jsonify(list(query))


@sales.post("/new")
def register_sale():
    body = request.get_json()

    try:
        sale = Sale.from_dict(body, request.headers.get("Authorization"))
    except (AssertionError, ValueError) as e:
        return jsonify({"message": str(e)}), 400

    _id = COLLECTION.insert_one(sale.to_bson()).inserted_id

    return jsonify({"message": "Success", "inserted_id": str(_id)}), 200


@sales.get("/filter")
def filter_sales():
    body = request.args

    filters = defaultdict(dict)
    ordering = {}

    if "username" in body:
        filters["customer.name"] = {"$regex": Regex(body["username"], "i")}

    # TODO: validate field types
    if "min" in body:
        filters["total"]["$gte"] = float(body["min"])

    if "max" in body:
        filters["total"]["$lte"] = float(body["max"])

    if "products" in body:
        filters["items._id"] = {"$in": body["products"].split(",")}

    if "status" in body:
        filters["status"] = body["status"]

    if "min_date" in body:
        filters["date"]["$gte"] = datetime.fromtimestamp(int(body["min_date"]) // 1000)

    if "max_date" in body:
        filters["date"]["$lte"] = datetime.fromtimestamp(int(body["max_date"]) // 1000)

    if "ordering" in body:
        symbol_mapping = {"+": pymongo.ASCENDING, "-": pymongo.DESCENDING}
        for ord in body["ordering"].split(","):
            key = ord[1:]
            direction = symbol_mapping.get(ord[0])

            if key in ["total", "date", "customer.name"] and direction is not None:
                ordering[key] = direction
            else:
                return jsonify({"message": f"Invalid ordering '{ord}'"}), 400

    if not ordering:
        ordering["_id"] = pymongo.ASCENDING

    count = int(body.get("count", 20))
    page = int(body.get("page", 1))
    pagination = [{"$skip": count * (page - 1)}, {"$limit": count}]

    query = COLLECTION.aggregate(
        BASE_QUERY + [{"$match": filters}, {"$sort": ordering}] + pagination
    )

    full_count = COLLECTION.aggregate(
        BASE_QUERY
        + [
            {"$match": filters},
            {"$sort": ordering},
            {"$group": {"_id": None, "count": {"$sum": 1}}},
        ]
    ).next()["count"]

    return jsonify({"match": list(query), "page_count": ceil(full_count / count)})
