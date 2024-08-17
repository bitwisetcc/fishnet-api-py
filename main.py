from os import environ

from bson import ObjectId
from dotenv import load_dotenv
from flask import Flask, jsonify, request
from flask_cors import CORS, cross_origin
from pymongo import MongoClient
from pymongo.server_api import ServerApi

load_dotenv()
app = Flask(__name__)
cors = CORS(app)
app.config["CORS_HEADERS"] = "Content-Type"

client = MongoClient(environ.get("MONGODB_URI"), server_api=ServerApi("1"))
db = client["FinFusion"]
collection = db["species"]


# Rota para obter todos os itens
@app.get("/itens")
@cross_origin()
def get_itens():
    itens = [{**doc, "_id": str(doc["_id"])} for doc in collection.find({})]
    return jsonify(itens)


# Rota para adicionar um novo item
@app.post("/itens")
@cross_origin()
def add_item():
    novo_item = request.json
    collection.insert_one(novo_item)
    return jsonify({"message": "Item adicionado com sucesso!"}), 201


# Buscar itens por nome, nome científico ou tag
@app.get("/itens/busca/<query>")
@cross_origin()
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


# Rota para obter um item específico pelo nome
@app.get("/itens/<product_id>")
@cross_origin()
def get_item(product_id):
    item = collection.find_one({"_id": ObjectId(product_id)}, {"_id": 0})
    if item:
        return jsonify(item)
    else:
        return jsonify({"error": "Item não encontrado"}), 404


# Rota para deletar um item pelo id
@app.delete("/itens/<product_id>")
@cross_origin()
def delete_item(product_id):
    result = collection.delete_one({"_id": ObjectId(product_id)})
    if result.deleted_count > 0:
        return jsonify({"message": "Item deletado com sucesso!"})
    else:
        return jsonify({"error": "Item não encontrado"}), 404


@app.post("/clientes")
@cross_origin()
def register_client():
    db["customer"].insert_one(request.json)
    # { is_company, name, email, phone, rg*1, cpf*1, cnpj*2, serial_CC, expiration_CC, backserial_CC, zip_code?, address? }
    return jsonify({"message": "Cliente registrado com sucesso!"}), 201


if __name__ == "__main__":
    app.run(debug=True)
