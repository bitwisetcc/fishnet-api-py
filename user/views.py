from math import ceil
from typing import Any

from bson import ObjectId
from flask import Blueprint, Response, abort, jsonify, request

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
@bearer_required("staff")
def get_users():
    try:
        query = parse_filters(request.args)
    except AssertionError as e:
        abort(400, description=e.args[0])

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
@bearer_required("staff")
def get_user_by_id(_, id):
    user = COLLECTION.find_one({"_id": ObjectId(id)})

    if not user:
        abort(404, description="User not found")

    return jsonify(to_dict(user)), 200


@users.delete("/<id>")
@bearer_required("manager")
def delete_user(_, id):
    transaction = COLLECTION.delete_one({"_id": ObjectId(id)})

    if not transaction.acknowledged:
        abort(404, "Usuário não encontrado")

    return Response(status=204)


@users.route("/self")
@bearer_required()
def user_profile(id: ObjectId):
    match request.method:
        case "GET":
            return jsonify(to_dict(COLLECTION.find_one({"_id": id}))), 200
        case "PUT":
            body = dict(request.get_json())
            transaction = COLLECTION.update_one({"_id": id}, {"$set": body})

            if not transaction.acknowledged:
                abort(500, description="Database failed to write data")

            return Response(status=204)
        case "DELETE":
            transaction = COLLECTION.delete_one({"_id": id})
            if not transaction.acknowledged:
                abort(500, description="Database failed to delete data")

            return Response(status=204)
