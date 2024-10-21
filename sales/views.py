from typing import Any
from bson import ObjectId
from flask import Blueprint, jsonify, request

from connections import db

collection = db["order"]
sales = Blueprint("sales", __name__)


def to_dict(item) -> dict[str, Any]:
    item["_id"] = str(item["id"])
    return item


@sales.get("/")
def get_sales():
    orders = collection.find()
    return jsonify(list(map(to_dict, orders)))
