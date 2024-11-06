from flask import Blueprint, jsonify
from datetime import datetime, timedelta
from connections import db
from bson.decimal128 import Decimal128

# Definindo o Blueprint
dashboard = Blueprint("dashboard", __name__)

# Coleções
order_collection = db['orders']
client_collection = db['users']

def calculate_order_total(order):
    return sum(float(item['price'].to_decimal()) * item['qty'] for item in order.get('items', []))

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
    total_vendas = round(sum(calculate_order_total(order) for order in vendas_do_mes), 2)

    # Clientes atingidos (clientes que fizeram pedidos este mês)
    clientes_atingidos = set(order.get('id_costumer') for order in vendas_do_mes)

    # Compras realizadas (total de pedidos)
    total_compras = len(vendas_do_mes)

    # Vendas do mês anterior
    vendas_ultimo_mes = list(order_collection.find({
        "date": {"$gte": primeiro_dia_ultimo_mes, "$lt": primeiro_dia_do_mes}
    }))
    total_vendas_ultimo_mes = sum(calculate_order_total(order) for order in vendas_ultimo_mes)

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

def to_dict(order):
    return {
        **order,
        "_id": str(order.get("_id")),
        "customer": str(order.get("id_customer", "")),
        "order_total": calculate_order_total(order),
        "date": order.get("date").isoformat() if order.get("date") else "",
        "status": str(order.get("status", ""))
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
        ultimo_dia_ultimo_mes = hoje.replace(day=1) - timedelta(seconds=1)
        start_date = primeiro_dia_ultimo_mes
        end_date = ultimo_dia_ultimo_mes.replace(hour=23, minute=59, second=59, microsecond=999999)
    elif period == "Este ano":
        start_date = hoje.replace(month=1, day=1)
        end_date = hoje.replace(hour=23, minute=59, second=59, microsecond=999999)
    elif period == "Ano passado":
        start_date = (hoje.replace(month=1, day=1) - timedelta(days=365))
        end_date = (hoje.replace(month=1, day=1) - timedelta(seconds=1))
    else:
        return jsonify({"error": "Período inválido"}), 400

    top_orders_pipeline = [
        {
            "$match": {
                "date": {"$gte": start_date, "$lt": end_date}
            }
        },
        {
            "$addFields": {
                "order_total": {"$sum": {"$map": {
                    "input": "$items",
                    "as": "item",
                    "in": {"$multiply": ["$$item.price", "$$item.qty"]}
                }}}
            }
        },
        {
            "$sort": {
                "order_total": -1
            }
        },
        {
            "$limit": 3
        }
    ]
    
    top_orders = list(order_collection.aggregate(top_orders_pipeline))
    return jsonify([to_dict(order) for order in top_orders]), 200

@dashboard.route('/annual-sales', methods=['GET'])
def get_annual_sales_data():
    start_of_year = datetime(datetime.now().year, 1, 1)
    monthly_sales_pipeline = [
        {"$match": {"date": {"$gte": start_of_year}}},
        {"$unwind": "$items"},
        {
            "$group": {
                "_id": {"month": {"$month": "$date"}},
                "total_sales": {
                    "$sum": {
                        "$multiply": ["$items.price", "$items.qty"] 
                    }
                }
            }
        },
        {
            "$sort": {"_id.month": 1} 
        }
    ]

    monthly_sales_data = list(order_collection.aggregate(monthly_sales_pipeline))

    def convert_decimal(value):
        if isinstance(value, Decimal128):
            return float(value.to_decimal())
        return value
    
    sales = {
        month["_id"]["month"]: convert_decimal(month.get("total_sales", 0))
        for month in monthly_sales_data
        if "_id" in month and "month" in month["_id"]
    }
    return jsonify(sales)