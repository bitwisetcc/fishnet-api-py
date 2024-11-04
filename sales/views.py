from collections import defaultdict
from datetime import datetime
from decimal import Decimal
from bson import Decimal128, ObjectId, Regex
from flask import Blueprint, current_app, jsonify, request
import jwt

from connections import db

sales = Blueprint("sales", __name__)
collection = db["orders_payment_details"]
customer_collection = db["users"]

# TODO: account for tax and shipping when calculating the total

BASE_QUERY = [
    {
        "$lookup": {
            "from": "users",
            "localField": "id_customer",
            "foreignField": "_id",
            "as": "user",
            "pipeline": [
                {"$project": {"name": 1}},
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
            "tax": {"$toDouble": "$tax"},
            "_id": {"$toString": "$_id"},
            "total": {
                "$toDouble": {
                    "$sum": [
                        {
                            "$sum": {
                                "$map": {
                                    "input": "$items",
                                    "as": "item",
                                    "in": "$$item.price",
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
]


@sales.get("/")
def get_all_orders():
    query = collection.aggregate(BASE_QUERY)
    return jsonify(list(query))


@sales.post("/new")
def register_sale():
    body = request.get_json()

    order = {}

    if "Authorization" in request.headers:
        try:
            payload = jwt.decode(
                request.headers["Authorization"],
                current_app.config["SECRET_KEY"],
                algorithms=["HS256"],
            )
        except jwt.DecodeError:
            return jsonify({"message": "Invalid token"}), 400

        order["customer_id"] = ObjectId(payload["sub"])
    else:
        customer = body.get("customer")

        if customer is None:
            return jsonify({"message": "Customer data not provided"}), 400

        required_fields = ["name", "surname", "addr", "cep", "email"]
        allowed_fields = required_fields + ["city", "state", "tel"]

        for f in required_fields:
            if f not in customer:
                return (
                    jsonify({"message": f"Missing required field: 'customer.{f}'"}),
                    400,
                )

        for f in customer:
            if f not in allowed_fields:
                return jsonify({"message": f"Unknown field: 'customer.{f}'"}), 400

        # TODO: avoid anonymous purchases from using existing e-mails
        order["customer"] = customer

    # TODO: use hashes for prices, or just hold a total. currently anyone can just pass any price they want, so you can buy 1000 Peixonautas for R$0.01 each
    order["items"] = []  # TODO: validate items
    for item in body["items"]:
        item["_id"] = ObjectId(item["id"])
        del item["id"]
        order["items"].append(item)

    order["tax"] = Decimal128(str(body["tax"]))
    order["shipping"] = Decimal128(str(body["shipping"]))
    order["shipping_provider"] = body.get("shipping", "Correios")

    if body["payment_method"] not in ["debit", "credit", "pix"]:
        return jsonify(
            {"message": f"Invalid payment method: '{body["payment_method"]}'"}, 400
        )

    order["payment_method"] = body["payment_method"]

    if body["payment_method"] != "pix":
        if body.get("payment_provider", None) is None:
            return jsonify(
                {
                    "message": "Missing field: 'payment_provider' required for card transactions"
                },
                400,
            )
        else:
            order["payment_provider"] = body["payment_provider"]

    order["status"] = body["status"]
    order["date"] = datetime.now()

    inserted_doc = collection.insert_one(order)

    # TODO: decrement items available quantity
    return (
        jsonify(
            {"message": f"Order successfully recorded: {inserted_doc.inserted_id}"}
        ),
        200,
    )


@sales.get("/filter")
def filter_sales():
    body = request.args

    filters = defaultdict(dict)
    ordering = {}
    symbol_mapping = {"+": 1, "-": -1}

    if "username" in body:
        filters["user.name"] = {"$regex": Regex(body["username"], "i")}

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
        for ord in body["ordering"].split(","):
            print(body)
            key = ord[1:]
            direction = symbol_mapping.get(ord[0])

            if key in ["total", "date", "user.name"] and direction is not None:
                ordering[key] = direction
            else:
                return jsonify({"message": f"Invalid ordering '{ord}'"}), 400

    if not ordering:
        ordering["_id"] = 1

    count = int(body.get("count", 20))
    page = int(body.get("page", 1))
    pagination = [{"$skip": count * (page - 1)}, {"$limit": count}]

    query = collection.aggregate(
        BASE_QUERY + [{"$match": filters}, {"$sort": ordering}] + pagination
    )

    return jsonify(list(query))
