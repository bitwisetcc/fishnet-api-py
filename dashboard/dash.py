from flask import Blueprint, jsonify
from datetime import datetime, timedelta
from connections import db

# Definindo o Blueprint
dashboard = Blueprint("dashboard", __name__)

# Coleções
order_collection = db['order']
client_collection = db['client']

# Rota para relatório mensal
@dashboard.route('/order', methods=['GET'])
def order():
    hoje = datetime.now()
    primeiro_dia_do_mes = hoje.replace(day=1)
    ultimo_mes = primeiro_dia_do_mes - timedelta(days=1)
    primeiro_dia_ultimo_mes = ultimo_mes.replace(day=1)

    # Vendas do mês atual
    vendas_do_mes = list(order_collection.find({
        "date": {"$gte": primeiro_dia_do_mes}
    }))
    total_vendas = sum(order.get('order_total', 0) for order in vendas_do_mes)

    # Clientes atingidos (clientes que fizeram pedidos este mês)
    clientes_atingidos = set(order.get('id_costumer') for order in vendas_do_mes)

    # Compras realizadas (total de pedidos)
    total_compras = len(vendas_do_mes)

    # Vendas do mês anterior
    vendas_ultimo_mes = list(order_collection.find({
        "date": {"$gte": primeiro_dia_ultimo_mes, "$lt": primeiro_dia_do_mes}
    }))
    total_vendas_ultimo_mes = sum(order.get('order_total', 0) for order in vendas_ultimo_mes)

    # Aumento em porcentagem em relação ao último mês
    aumento_em_porcentagem = 0.0
    if total_vendas_ultimo_mes > 0:
        aumento_em_porcentagem = ((total_vendas - total_vendas_ultimo_mes) / total_vendas_ultimo_mes) * 100

    # Montando o relatório
    relatorio = {
        "total_vendas": total_vendas,
        "aumento_em_porcentagem": aumento_em_porcentagem,
        "clientes_atingidos": len(clientes_atingidos),
        "total_compras_realizadas": total_compras,
    }

    return jsonify(relatorio)

def to_dict(item):
    return {
        **item,
        "_id": str(item["_id"]),
        "customer": str(item["customer"]),
        "order_total": float(item.get("order_total", 0)),
        "date": datetime.strptime(item["date"], "%Y-%m-%d %H:%M:%S"),
        "status": str(item["status"])
    }
    
@dashboard.route('/order/top3/<string:period>', methods=['GET'])
def get_top_3(period):
    hoje = datetime.now()
    if period == "Hoje":
        start_date = hoje.replace(hour=0, minute=0, second=0, microsecond=0)
        end_date = hoje.replace(hour=23, minute=59, second=59, microsecond=999999)
    elif period == "Ontem":
        start_date = (hoje - timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        end_date = (hoje - timedelta(days=1)).replace(hour=23, minute=59, second=59, microsecond=999999)
    elif period == "Semana":
        start_date = hoje - timedelta(days=hoje.weekday())
        end_date = hoje.replace(hour=23, minute=59, second=59, microsecond=999999)
    elif period == "Mês":
        start_date = hoje.replace(day=1)
        end_date = hoje.replace(hour=23, minute=59, second=59, microsecond=999999)
    elif period == "Mês passado":
        primeiro_dia_ultimo_mes = (hoje.replace(day=1) - timedelta(days=1)).replace(day=1)
        ultimo_dia_ultimo_mes = hoje.replace(day=1) - timedelta(days=1)
        start_date = primeiro_dia_ultimo_mes
        end_date = ultimo_dia_ultimo_mes.replace(hour=23, minute=59, second=59, microsecond=999999)
    elif period == "Este ano":
        start_date = hoje.replace(month=1, day=1)
        end_date = hoje.replace(hour=23, minute=59, second=59, microsecond=999999)
    elif period == "Ano passado":
        start_date = (hoje.replace(month=1, day=1) - timedelta(days=365))
        end_date = (hoje.replace(month=1, day=1) - timedelta(days=1)).replace(hour=23, minute=59, second=59, microsecond=999999)

    top_orders = list(order_collection.find({
        "date": {"$gte": start_date, "$lt": end_date}
    }).sort("order_total", -1).limit(3))

    return jsonify([to_dict(order) for order in top_orders]), 200