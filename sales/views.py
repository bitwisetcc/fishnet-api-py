import io
from collections import defaultdict
from datetime import datetime
from math import ceil
from typing import Any

import pymongo
from bson import ObjectId, Regex
from flask import Blueprint, abort, jsonify, request, send_file

from connections import db
from decorators import Role, bearer_required
from sales.models import Sale, parse_filters
from sales.queries import BASE_QUERY, LOOKUP_PRODUCTS

sales = Blueprint("sales", __name__)

COLLECTION = db["orders"]
CUSTOMERS = db["users"]
PRODUCTS = db["species"]


@sales.get("/")
def get_products():
    try:
        query = parse_filters(request.args)
    except AssertionError as e:
        abort(400, description=e.args[0])

    count = int(request.args.get("count", 20))
    page = int(request.args.get("page", 1))
    pagination = [{"$skip": count * (page - 1)}, {"$limit": count}]

    query = COLLECTION.aggregate(BASE_QUERY + query + pagination)

    full_count_result = COLLECTION.aggregate(
        BASE_QUERY + query + [{"$group": {"_id": None, "count": {"$sum": 1}}}]
    )

    full_count = full_count_result.next().get("count", 0)

    if full_count == 0:
        return jsonify({"match": [], "page_count": 0})

    return jsonify({"match": list(query), "page_count": ceil(full_count / count)})


@sales.post("/")
@bearer_required(Role.STAFF)
def register_sale():
    body = request.get_json()

    try:
        sale: Sale = Sale.from_dict(body, request.headers.get("Authorization"))
    except (AssertionError, ValueError) as e:
        return jsonify({"message": str(e)}), 400

    _id = COLLECTION.insert_one(sale.to_bson()).inserted_id

    sale.items

    for prod in sale.items:
        res = PRODUCTS.update_one({"_id": prod.id}, {"$inc": {"quantity": -prod.qty}})
        print(res)

    return jsonify({"message": "Success", "inserted_id": str(_id)}), 200


@sales.get("/report/<id>")
def get_report(id):
    sale = COLLECTION.aggregate(
        [{"$match": {"_id": ObjectId(id)}}] + LOOKUP_PRODUCTS + BASE_QUERY
    ).next()

    pdf = Sale.generate_report(sale)

    return send_file(
        io.BytesIO(pdf.output(dest="S")), mimetype="application/pdf", as_attachment=True
    )
