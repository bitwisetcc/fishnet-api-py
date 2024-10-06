from flask import Flask, jsonify
from pymongo import MongoClient
from datetime import datetime, timedelta
from bson.objectid import ObjectId

app = Flask(__name__)

# Conectar ao MongoDB
client = MongoClient("mongodb+srv://api-tester:QyHLaCgakHRjtn9n@finfusion1.uzpenme.mongodb.net/?retryWrites=true&w=majority&appName=FinFusion1")
db = client['FinFusion']

# Coleções
order_collection = db['order']
order_items_collection = db['order_items']
users_collection = db['users']

# Rota para relatório mensal
@app.route('/order', methods=['GET'])
def relatorio_mensal():
    hoje = datetime.now()
    primeiro_dia_do_mes = hoje.replace(day=1)
    ultimo_mes = primeiro_dia_do_mes - timedelta(days=1)
    primeiro_dia_ultimo_mes = ultimo_mes.replace(day=1)

    # Vendas do mês atual
    vendas_do_mes = list(order_collection.find({
        "date": {"$gte": primeiro_dia_do_mes}
    }))
    total_vendas = sum(order['order_total'] for order in vendas_do_mes)

    # Clientes atingidos (clientes que fizeram pedidos este mês)
    clientes_atingidos = set(order['id_costumer'] for order in vendas_do_mes)

    # Compras realizadas (total de pedidos)
    total_compras = len(vendas_do_mes)

    # Vendas do mês anterior
    vendas_ultimo_mes = list(order_collection.find({
        "date": {"$gte": primeiro_dia_ultimo_mes, "$lt": primeiro_dia_do_mes}
    }))
    total_vendas_ultimo_mes = sum(order['total'] for order in vendas_ultimo_mes)

    # Aumento em porcentagem em relação ao último mês
    if total_vendas_ultimo_mes > 0:
        aumento_em_porcentagem = ((total_vendas - total_vendas_ultimo_mes) / total_vendas_ultimo_mes) * 100
    else:
        aumento_em_porcentagem = 100.0 if total_vendas > 0 else 0.0  # Se não houve vendas no mês anterior, consideramos um aumento de 100% se houver vendas no mês atual.

    # Montando o relatório
    relatorio = {
        "total_vendas": total_vendas,
        "aumento_em_porcentagem": aumento_em_porcentagem,
        "clientes_atingidos": len(clientes_atingidos),
        "total_compras_realizadas": total_compras,
    }

    return jsonify(relatorio)

if __name__ == '__main__':
    app.run(debug=True)
