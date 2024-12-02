from collections import defaultdict
from datetime import datetime
from math import ceil

from bson import Regex
from flask import Blueprint, jsonify, request
import pymongo

from connections import db
from sales.validation import Sale
from datetime import datetime

sales = Blueprint("sales", __name__)
COLLECTION = db["orders"]
CUSTOMERS = db["users"]
PRODUCTS = db["species"]


BASE_QUERY = [
    {
        "$lookup": {
            "from": "users",
            "localField": "customer_id",
            "foreignField": "_id",
            "as": "user",
            "pipeline": [
                {"$project": {"name": 1, "email": 1}},
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
        sale: Sale = Sale.from_dict(body, request.headers.get("Authorization"))
    except (AssertionError, ValueError) as e:
        return jsonify({"message": str(e)}), 400

    _id = COLLECTION.insert_one(sale.to_bson()).inserted_id

    sale.items

    for prod in sale.items:
        res = PRODUCTS.update_one({ "_id": prod.id }, { "$inc": { "quantity": -prod.qty} })
        print(res)

    return jsonify({"message": "Success", "inserted_id": str(_id)}), 200


def parse_date(date_str):
    try:
        # Tentar converter a data no formato ISO 8601 (exemplo: "2023-11-24")
        return datetime.fromisoformat(date_str)
    except ValueError:
        # Se não for nesse formato, tentar como timestamp em milissegundos
        try:
            return datetime.fromtimestamp(int(date_str) // 1000)
        except ValueError:
            raise ValueError(f"Invalid date format: {date_str}")


@sales.get("/filter")
def filter_sales():
    body = request.args

    filters = defaultdict(dict)
    ordering = {}

    if "username" in body:
        filters["customer.name"] = {"$regex": Regex(body["username"], "i")}

    if "payment_method" in body:
        filters["payment_method"] = {"$regex": Regex(body["payment_method"], "i")}

    if "status" in body:
        try:
            filters["status"] = int(body["status"])
        except ValueError:
            return jsonify({"message": "Invalid 'status' value"}), 400

    if "min_price" in body:
        filters["total"]["$gte"] = float(body["min_price"])

    if "max_price" in body:
        filters["total"]["$lte"] = float(body["max_price"])

    if "products" in body:
        filters["items._id"] = {"$in": body["products"].split(",")}

    if "min_date" in body:
        try:
            filters["date"]["$gte"] = parse_date(body["min_date"])
        except ValueError as e:
            return jsonify({"message": str(e)}), 400

    if "max_date" in body:
        try:
            filters["date"]["$lte"] = parse_date(body["max_date"])
        except ValueError as e:
            return jsonify({"message": str(e)}), 400

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

    full_count_result = COLLECTION.aggregate(
        BASE_QUERY
        + [
            {"$match": filters},
            {"$sort": ordering},
            {"$group": {"_id": None, "count": {"$sum": 1}}},
        ]
    )

    full_count = 0
    for result in full_count_result:
        full_count = result.get(
            "count", 0
        )  # Usar 0 como valor padrão caso 'count' não exista

    # Se não houver nenhum resultado, a contagem de páginas deve ser zero
    if full_count == 0:
        return jsonify({"match": [], "page_count": 0})

    # Retornar o número total de páginas
    return jsonify({"match": list(query), "page_count": ceil(full_count / count)})
