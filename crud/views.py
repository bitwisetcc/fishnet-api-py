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


# Rotas CRUD - Customer (Clientes)
@crud.route("/customer", methods=["POST"])
@validate()
def create_customer():
    customer = request.json
    result = customer_collection.insert_one(customer)
    return jsonify(str(result.inserted_id)), 201


@crud.route("/customer", methods=["GET"])
def get_customers():
    customers = list(customer_collection.find())
    return jsonify([to_dict(c) for c in customers]), 200


@crud.route("/customer/<id>", methods=["GET"])
def get_customer_by_id(id):
    customer = customer_collection.find_one({"_id": ObjectId(id)})
    if customer:
        return jsonify(to_dict(customer)), 200
    return jsonify({"error": "Customer not found"}), 404


@crud.route("/customer/<id>", methods=["PUT"])
@validate()
def update_customer(id):
    updated_customer = request.json
    result = customer_collection.update_one(
        {"_id": ObjectId(id)}, {"$set": updated_customer}
    )
    if result.matched_count:
        return jsonify({"message": "Customer updated"}), 200
    return jsonify({"error": "Customer not found"}), 404


@crud.route("/customer/<id>", methods=["DELETE"])
def delete_customer(id):
    result = customer_collection.delete_one({"_id": ObjectId(id)})
    if result.deleted_count:
        return jsonify({"message": "Customer deleted"}), 200
    return jsonify({"error": "Customer not found"}), 404


# Rotas CRUD - Employee (Funcionários)
@crud.route("/employee", methods=["POST"])
@validate()
def create_employee():
    employee = request.json
    result = employee_collection.insert_one(employee)
    return jsonify(str(result.inserted_id)), 201


@crud.route("/employee", methods=["GET"])
def get_employees():
    employees = list(employee_collection.find())
    return jsonify([to_dict(e) for e in employees]), 200


@crud.route("/employee/<id>", methods=["GET"])
def get_employee_by_id(id):
    employee = employee_collection.find_one({"_id": ObjectId(id)})
    if employee:
        return jsonify(to_dict(employee)), 200
    return jsonify({"error": "Employee not found"}), 404


@crud.route("/employee/<id>", methods=["PUT"])
@validate()
def update_employee(id):
    updated_employee = request.json
    result = employee_collection.update_one(
        {"_id": ObjectId(id)}, {"$set": updated_employee}
    )
    if result.matched_count:
        return jsonify({"message": "Employee updated"}), 200
    return jsonify({"error": "Employee not found"}), 404


@crud.route("/employee/<id>", methods=["DELETE"])
def delete_employee(id):
    result = employee_collection.delete_one({"_id": ObjectId(id)})
    if result.deleted_count:
        return jsonify({"message": "Employee deleted"}), 200
    return jsonify({"error": "Employee not found"}), 404
