from math import ceil
from bson import Decimal128, ObjectId
from flask import Blueprint, jsonify, request
import pymongo

from connections import db

products = Blueprint("products", __name__)
collection = db["species"]
orders_collection = db["orders"]


# TODO: upload images to some storage bucket and store the URLs


def to_dict(item):
    item["_id"] = str(item["_id"])
    item["price"] = float(item["price"].to_decimal())
    return item


@products.get("/")
def get_species():
    species = list(collection.find())
    return jsonify([to_dict(f) for f in species]), 200


@products.post("/new")
def post_species():
    species = request.get_json()
    species["price"] = Decimal128(species["price"])
    result = collection.insert_one(species)
    return jsonify(str(result.inserted_id)), 201


@products.get("/<id>")
def get_species_by_id(id):
    species = collection.find_one({"_id": ObjectId(id)})
    if species is None:
        return jsonify({"error": "Species not found"}), 404

    return (jsonify(to_dict(species)), 200)


@products.put("/<id>")
def update_species(id):
    updated_species = request.json
    result = collection.update_one({"_id": ObjectId(id)}, {"$set": updated_species})
    if result.matched_count:
        return jsonify({"message": "Species updated"}), 200
    return jsonify({"error": "Species not found"}), 404


@products.delete("/<id>")
def delete_species(id):
    result = collection.delete_one({"_id": ObjectId(id)})
    if result.deleted_count:
        return jsonify({"message": "Species deleted"}), 200
    return jsonify({"error": "Species not found"}), 404


@products.get("/busca/<query>")
def get_itens_by_query(query):
    itens = [
        {**doc, "_id": str(doc["_id"])}
        for doc in collection.find(
            {
                "$or": [
                    {field: {"$regex": query}}
                    for field in ["name", "scientificName", "tags"]
                ]
            },
        )
    ]

    return jsonify(itens)


@products.get("/filtros")
def get_itens_by_filter():
    name = request.args.get("name", "")
    tags = request.args.get("tags")
    lancamento = request.args.get("lancamento")
    ordem = request.args.get("ordem")
    habitat = request.args.get("habitat")
    feeding = request.args.get("feeding")
    ofertas = request.args.get("ofertas")
    min_price = request.args.get("minPrice")
    max_price = request.args.get("maxPrice")
    min_size = request.args.get("minSize")
    max_size = request.args.get("maxSize")
    behavior = request.args.get("behavior")
    ecosystem = request.args.get("ecosystem")

    filter_conditions = []

    if name:
        filter_conditions.append(
            {
                "$or": [
                    {"name": {"$regex": name, "$options": "i"}},
                    {"scientificName": {"$regex": name, "$options": "i"}},
                ]
            }
        )

    if tags:
        filter_conditions.append({"tags": {"$regex": tags, "$options": "i"}})

    if lancamento:
        filter_conditions.append({"lancamento": lancamento})

    if habitat:
        filter_conditions.append({"habitat": {"$regex": habitat, "$options": "i"}})

    if feeding:
        filter_conditions.append({"feeding": {"$regex": feeding, "$options": "i"}})

    if behavior:
        filter_conditions.append(
            {"social_behavior": {"$regex": behavior, "$options": "i"}}
        )

    if ecosystem:
        filter_conditions.append({"ecosystem": {"$regex": ecosystem, "$options": "i"}})

    if ofertas:
        filter_conditions.append({"ofertas": True})

    if min_price or max_price:
        price_filter = {}
        if min_price:
            price_filter["$gte"] = float(min_price.replace("$", "").strip())
        if max_price:
            price_filter["$lte"] = float(max_price.replace("$", "").strip())
        filter_conditions.append({"price": price_filter})

    if min_size or max_size:
        size_filter = {}
        if min_size:
            size_filter["$gte"] = float(min_size)
        if max_size:
            size_filter["$lte"] = float(max_size)
        filter_conditions.append({"size": size_filter})

    final_filter = {"$and": filter_conditions} if filter_conditions else {}

    sort_criteria = []
    if ordem:
        if ordem == "A-Z":
            sort_criteria.append(("name", 1))  # Ordena de A-Z
        elif ordem == "Z-A":
            sort_criteria.append(("name", -1))  # Ordena de Z-A
        elif ordem == "crescente":
            sort_criteria.append(("price", 1))  # Ordena por preço crescente
        elif ordem == "decrescente":
            sort_criteria.append(("price", -1))  # Ordena por preço decrescente
    else:
        sort_criteria = [("_id", pymongo.ASCENDING)]

    count = int(request.args.get("count", 20))
    page = int(request.args.get("page", 1))

    query = collection.find(final_filter).sort(sort_criteria)
    total = collection.count_documents(final_filter)

    itens = [to_dict(doc) for doc in query.skip(count * (page - 1)).limit(count)]

    return jsonify({"match": itens, "page_count": ceil(total / count)})

@products.get("/getotal")
def get_total():
    product_id = request.args.get("product_id")
    if not product_id:
        return jsonify({"error": "Product ID is required"}), 400

    try:
        product_id = ObjectId(product_id)
    except Exception:
        return jsonify({"error": "Invalid Product ID format"}), 400

    pipeline = [
        {"$unwind": "$items"},
        {"$match": {"items._id": product_id, "status": "completed"}},
        {"$group": {"_id": None, "total": {"$sum": "$items.qty"}}} 
    ]

    total_sold = list(orders_collection.aggregate(pipeline))

    if total_sold:
        return jsonify({"total_sold": total_sold[0]["total"]}), 200
    else:
        return jsonify({"total_sold": 0}), 200