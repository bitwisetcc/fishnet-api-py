from flask import Blueprint, jsonify
from datetime import datetime, timedelta
from connections import db
from bson import ObjectId

dashboard = Blueprint("dashboard", __name__)

order_collection = db["orders_real_users"]
client_collection = db["users"]


@dashboard.route("/order", methods=["GET"])
def order():
    hoje = datetime.now()
    primeiro_dia_do_mes = hoje.replace(day=1)
    ultimo_mes = primeiro_dia_do_mes - timedelta(days=1)
    primeiro_dia_ultimo_mes = ultimo_mes.replace(day=1)

    vendas_do_mes_pipeline = [
        {"$match": {"date": {"$gte": primeiro_dia_do_mes}}},
        {"$unwind": "$items"},
        {
            "$group": {
                "_id": None,
                "total_vendas": {"$sum": {"$multiply": ["$items.price", "$items.qty"]}},
                "clientes_atingidos": {"$addToSet": "$id_customer"},
                "total_compras": {"$sum": 1},
            }
        },
    ]

    vendas_do_mes = [to_dict(doc) for doc in vendas_do_mes] if vendas_do_mes else []

    total_vendas = vendas_do_mes[0].get("total_vendas", 0) if vendas_do_mes else 0
    clientes_atingidos = (
        len(vendas_do_mes[0].get("clientes_atingidos", [])) if vendas_do_mes else 0
    )
    total_compras = vendas_do_mes[0].get("total_compras", 0) if vendas_do_mes else 0

    vendas_ultimo_mes_pipeline = [
        {
            "$match": {
                "date": {"$gte": primeiro_dia_ultimo_mes, "$lt": primeiro_dia_do_mes}
            }
        },
        {"$unwind": "$items"},
        {
            "$group": {
                "_id": None,
                "total_vendas": {"$sum": {"$multiply": ["$items.price", "$items.qty"]}},
            }
        },
    ]

    vendas_ultimo_mes = list(order_collection.aggregate(vendas_ultimo_mes_pipeline))
    total_vendas_ultimo_mes = (
        vendas_ultimo_mes[0].get("total_vendas", 0) if vendas_ultimo_mes else 0
    )

    aumento_em_porcentagem = 0.0
    if total_vendas_ultimo_mes > 0:
        aumento_em_porcentagem = (
            (total_vendas - total_vendas_ultimo_mes) / total_vendas_ultimo_mes
        ) * 100

    relatorio = {
        "total_vendas": total_vendas,
        "aumento_em_porcentagem": aumento_em_porcentagem,
        "clientes_atingidos": clientes_atingidos,
        "total_compras_realizadas": total_compras,
    }

    return jsonify(relatorio)


def to_dict(item):
    return {
        **{k: str(v) if isinstance(v, ObjectId) else v for k, v in item.items()},
        "date": item.get("date").isoformat() if item.get("date") else "",
    }


@dashboard.route("/order/top3/<string:period>", methods=["GET"])
def get_top_3(period):
    hoje = datetime.now()

    if period == "Hoje":
        start_date = hoje.replace(hour=0, minute=0, second=0, microsecond=0)
        end_date = hoje.replace(hour=23, minute=59, second=59, microsecond=999999)
    elif period == "Ontem":
        start_date = (hoje - timedelta(days=1)).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        end_date = (hoje - timedelta(days=1)).replace(
            hour=23, minute=59, second=59, microsecond=999999
        )
    elif period == "Semana":
        start_date = hoje - timedelta(days=hoje.weekday())
        end_date = hoje.replace(hour=23, minute=59, second=59, microsecond=999999)
    elif period == "Mês":
        start_date = hoje.replace(day=1)
        end_date = hoje.replace(hour=23, minute=59, second=59, microsecond=999999)
    elif period == "Mês passado":
        primeiro_dia_ultimo_mes = (hoje.replace(day=1) - timedelta(days=1)).replace(
            day=1
        )
        ultimo_dia_ultimo_mes = hoje.replace(day=1) - timedelta(seconds=1)
        start_date = primeiro_dia_ultimo_mes
        end_date = ultimo_dia_ultimo_mes.replace(
            hour=23, minute=59, second=59, microsecond=999999
        )
    elif period == "Este ano":
        start_date = hoje.replace(month=1, day=1)
        end_date = hoje.replace(hour=23, minute=59, second=0, microsecond=0)
    elif period == "Ano passado":
        start_date = hoje.replace(month=1, day=1) - timedelta(days=365)
        end_date = hoje.replace(month=1, day=1) - timedelta(seconds=1)
    else:
        return jsonify({"error": "Período inválido"}), 400

    top_orders_pipeline = [
        {"$match": {"date": {"$gte": start_date, "$lt": end_date}}},
        {"$unwind": "$items"},
        {
            "$group": {
                "_id": "$_id",
                "order_total": {"$sum": {"$multiply": ["$items.price", "$items.qty"]}},
                "id_customer": {"$first": "$id_customer"},
                "date": {"$first": "$date"},
                "status": {"$first": "$status"},
            }
        },
        {"$sort": {"order_total": -1}},
        {"$limit": 3},
    ]

    top_orders = list(order_collection.aggregate(top_orders_pipeline))
    top_orders = [to_dict(order) for order in top_orders] if top_orders else []
    return jsonify(top_orders), 200

@dashboard.route("/annual-sales", methods=["GET"])
def get_annual_sales_data():
    start_of_year = datetime(datetime.now().year, 1, 1)
    monthly_sales_pipeline = [
        {
            "$match": {
                "date": {"$gte": start_of_year}
            }
        },
        {
            "$unwind": "$items" 
        },
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
    
    sales = {month["_id"]["month"]: month.get("total_sales", 0) for month in monthly_sales_data if "_id" in month and "month" in month["_id"]}
    return jsonify(sales)
