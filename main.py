from os import environ

from dotenv import load_dotenv
from flask import Flask, jsonify, request
from pymongo import MongoClient
from pymongo.server_api import ServerApi

load_dotenv()
app = Flask(__name__)

client = MongoClient(environ.get("MONGODB_URI"), server_api=ServerApi("1"))
db = client["FinFusion"]
collection = db["species"]


# Rota para obter todos os itens
@app.get("/itens")
def get_itens():
    itens = list(collection.find({}, {"_id": 0}))  # Remove o campo _id da resposta
    return jsonify(itens)


# Rota para adicionar um novo item
@app.post("/itens")
def add_item():
    novo_item = request.json
    collection.insert_one(novo_item)
    return jsonify({"message": "Item adicionado com sucesso!"}), 201


# Buscar itens por nome e nome científico
@app.get("/itens/busca/<query>")
def get_itens_by_query(query):
    itens = list(collection.find({"name_species": {"$regex": query}}, {"_id": 0}))
    return jsonify(itens)


# Rota para obter um item específico pelo nome
@app.get("/itens/<nome>")
def get_item(nome):
    item = collection.find_one({"nome": nome}, {"_id": 0})
    if item:
        return jsonify(item)
    else:
        return jsonify({"error": "Item não encontrado"}), 404


# Rota para deletar um item pelo nome
@app.delete("/itens/<nome>")
def delete_item(nome):
    result = collection.delete_one({"nome": nome})
    if result.deleted_count > 0:
        return jsonify({"message": "Item deletado com sucesso!"})
    else:
        return jsonify({"error": "Item não encontrado"}), 404


if __name__ == "__main__":
    app.run(debug=True)
