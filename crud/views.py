from bson import ObjectId
from flask import Blueprint, jsonify, request
from flask_pydantic import validate

from connections import db

species_collection = db["teste_species"]
customer_collection = db["customer"]
employee_collection = db["employee"]

crud = Blueprint("crud", __name__)


# Conversão de ObjectId
def to_dict(item):
    item["_id"] = str(item["_id"])
    return item


# Rotas CRUD - Species (Produtos)
@crud.post("/species")
@validate()
def create_species():
    species = request.json
    result = species_collection.insert_one(species)
    return jsonify(str(result.inserted_id)), 201


@crud.get("/species")
def get_species():
    species = list(species_collection.find())
    return jsonify([to_dict(f) for f in species]), 200


@crud.get("/species/<id>")
def get_species_by_id(id):
    species = species_collection.find_one({"_id": ObjectId(id)})
    if species is None:
        return jsonify({"error": "Species not found"}), 404

    return (
        jsonify(
            {
                **species,
                "_id": str(species["_id"]),
                "price": species["price"].to_decimal(),
            }
        ),
        200,
    )


@crud.put("/species/<id>")
@validate()
def update_species(id):
    updated_species = request.json
    result = species_collection.update_one(
        {"_id": ObjectId(id)}, {"$set": updated_species}
    )
    if result.matched_count:
        return jsonify({"message": "Species updated"}), 200
    return jsonify({"error": "Species not found"}), 404


@crud.delete("/species/<id>")
def delete_species(id):
    result = species_collection.delete_one({"_id": ObjectId(id)})
    if result.deleted_count:
        return jsonify({"message": "Species deleted"}), 200
    return jsonify({"error": "Species not found"}), 404
