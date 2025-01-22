import io
from math import ceil

from bson import ObjectId
from bson.errors import InvalidId
from flask import Blueprint, Response, abort, jsonify, request, send_file
from jsonschema import ValidationError, validate

from connections import db
from decorators import Role, bearer_required
from sales.models import SALE_SCHEMA, generate_report, parse_filters
from sales.queries import BASE_QUERY, LOOKUP_PRODUCTS

sales = Blueprint("sales", __name__)

COLLECTION = db["orders"]
CUSTOMERS = db["users"]
PRODUCTS = db["species"]


@sales.get("/")
@bearer_required(Role.STAFF)
def get_sales():
    try:
        query = parse_filters(request.args)
    except AssertionError as e:
        abort(400, e.args[0])

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


@sales.post("/buy")
def register_sale():
    sale = dict(request.get_json())

    try:
        validate(sale, SALE_SCHEMA)
    except ValidationError as e:
        abort(400, f"Validação falha: {e.args[0]}")

    try:
        matching_products = list(
            PRODUCTS.find(
                {"_id": {"$in": [ObjectId(item["_id"]) for item in sale["items"]]}}
            )
        )
    except InvalidId as e:
        abort(400, "Item com id inválido: {}".format("".join(e.args[0].split("'")[:2])))

    if len(matching_products) != len(sale["items"]):
        abort(400, "Id de item inválido")

    for item, prod in zip(sale["items"], matching_products):
        item["price"] = prod["price"]

    # TODO: add customer_id for token auth
    if (request.headers.get("Authorization") is None) and ("customer" not in sale):
        abort(400, "Informação do cliente ausente")
    if (request.headers.get("Authorization") is not None) == ("customer" in sale):
        abort(400, "Multiplas fontes de informação de cliente")

    if sale["payment_method"] == "pix" and "payment_provider" in sale:
        abort(400, "Pagamentos em PIX não apresentam provedor")

    COLLECTION.insert_one(sale)

    for prod in sale["items"]:
        PRODUCTS.update_one(
            {"_id": prod["_id"]}, {"$inc": {"quantity": -prod["quantity"]}}
        )

    return Response(status=204)


@sales.get("/report/<id>")
def get_report(id):
    sale = COLLECTION.aggregate(
        [{"$match": {"_id": ObjectId(id)}}] + LOOKUP_PRODUCTS + BASE_QUERY
    ).next()

    pdf = generate_report(sale)

    return send_file(
        io.BytesIO(pdf.output(dest="S")), mimetype="application/pdf", as_attachment=True
    )
