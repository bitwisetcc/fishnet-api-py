from os import environ

from bson import ObjectId
from dotenv import load_dotenv
from flask import Flask, jsonify, request
from flask_cors import CORS, cross_origin

from connections import db
from auth.views import auth
from crud.views import crud
from user.views import users

species = db["species"]
customers = db["customers"]

load_dotenv()

app = Flask(__name__)
cors = CORS(app)
app.config["CORS_HEADERS"] = "Content-Type"
app.config["SECRET_KEY"] = environ.get("SECRET_KEY", ":^)")

app.register_blueprint(auth, url_prefix="/auth")
app.register_blueprint(users, url_prefix="/users")
app.register_blueprint(crud, url_prefix="/crud")


# Rota para obter todos os itens
@app.get("/itens")
@cross_origin()
def get_itens():
    itens = [{**doc, "_id": str(doc["_id"])} for doc in species.find({})]
    return jsonify(itens)


# Rota para adicionar um novo item
@app.post("/itens")
@cross_origin()
def add_item():
    novo_item = request.json
    species.insert_one(novo_item)
    return jsonify({"message": "Item adicionado com sucesso!"}), 201


# Buscar itens por nome, nome científico ou tag
@app.get("/itens/busca/<query>")
@cross_origin()
def get_itens_by_query(query):
    itens = [
        {**doc, "_id": str(doc["_id"])}
        for doc in species.find(
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
    item = species.find_one({"_id": ObjectId(product_id)}, {"_id": 0})
    if item:
        return jsonify(item)
    else:
        return jsonify({"error": "Item não encontrado"}), 404


# Rota para deletar um item pelo id
@app.delete("/itens/<product_id>")
@cross_origin()
def delete_item(product_id):
    result = species.delete_one({"_id": ObjectId(product_id)})
    if result.deleted_count > 0:
        return jsonify({"message": "Item deletado com sucesso!"})
    else:
        return jsonify({"error": "Item não encontrado"}), 404


@app.get("/itens/filtros")
@cross_origin()
def get_itens_by_filter():
    name = request.args.get("name", "")
    tags = request.args.get("tags")
    lancamento = request.args.get("lancamento")
    ordem_alfabetica = request.args.get("ordemAlfabetica")
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

    if filter_conditions:
        final_filter = (
            {"$and": filter_conditions}
            if len(filter_conditions) > 1
            else filter_conditions[0]
        )
    else:
        final_filter = {}

    sort_criteria = None
    if ordem_alfabetica == "A-Z":
        sort_criteria = [("name", 1)]  # Ordena de A-Z
    elif ordem_alfabetica == "Z-A":
        sort_criteria = [("name", -1)]  # Ordena de Z-A

    if sort_criteria:
        itens = [
            {**doc, "_id": str(doc["_id"])}
            for doc in species.find(final_filter).sort(sort_criteria)
        ]
    else:
        itens = [{**doc, "_id": str(doc["_id"])} for doc in species.find(final_filter)]

    return jsonify(itens)


@app.post("/clientes")
@cross_origin()
def register_client():
    customers.insert_one(request.json)
    # { is_company, name, email, phone, rg*1, cpf*1, cnpj*2, serial_CC, expiration_CC, backserial_CC, zip_code?, address? }
    return jsonify({"message": "Cliente registrado com sucesso!"}), 201


if __name__ == "__main__":
    app.run(debug=True)
