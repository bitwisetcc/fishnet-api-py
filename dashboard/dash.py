from flask import Blueprint, jsonify
from datetime import datetime, timedelta
from connections import db

# Definindo o Blueprint
dashboard = Blueprint("dashboard", __name__)

# Coleções
order_collection = db['order']
client_collection = db['client']

# Rota para relatório mensal
@dashboard.route("/order", methods=["GET"])
def order():
    hoje = datetime.now()
    primeiro_dia_do_mes = hoje.replace(day=1)
    ultimo_mes = primeiro_dia_do_mes - timedelta(days=1)
    primeiro_dia_ultimo_mes = ultimo_mes.replace(day=1)

    # Vendas do mês atual usando agregação
    vendas_do_mes_pipeline = [
        {
            "$match": {
                "date": {"$gte": primeiro_dia_do_mes}
            }
        },
        {
            "$group": {
                "_id": None,
                "total_vendas": {"$sum": {"$toDouble": "$order_total"}},
                "clientes_atingidos": {"$addToSet": "$id_customer"},
                "total_compras": {"$sum": 1}
            }
        }
    ]
    
    vendas_do_mes = list(order_collection.aggregate(vendas_do_mes_pipeline))
    
    total_vendas = vendas_do_mes[0]["total_vendas"] if vendas_do_mes else 0
    clientes_atingidos = len(vendas_do_mes[0]["clientes_atingidos"]) if vendas_do_mes else 0
    total_compras = vendas_do_mes[0]["total_compras"] if vendas_do_mes else 0

    # Vendas do mês anterior usando agregação
    vendas_ultimo_mes_pipeline = [
        {
            "$match": {
                "date": {"$gte": primeiro_dia_ultimo_mes, "$lt": primeiro_dia_do_mes}
            }
        },
        {
            "$group": {
                "_id": None,
                "total_vendas": {"$sum": {"$toDouble": "$order_total"}}
            }
        }
    ]
    
    vendas_ultimo_mes = list(order_collection.aggregate(vendas_ultimo_mes_pipeline))
    total_vendas_ultimo_mes = vendas_ultimo_mes[0]["total_vendas"] if vendas_ultimo_mes else 0

    # Aumento em porcentagem em relação ao último mês
    aumento_em_porcentagem = 0.0
    if total_vendas_ultimo_mes > 0:
        aumento_em_porcentagem = (
            (total_vendas - total_vendas_ultimo_mes) / total_vendas_ultimo_mes
        ) * 100

    # Montando o relatório
    relatorio = {
        "total_vendas": total_vendas,
        "aumento_em_porcentagem": aumento_em_porcentagem,
        "clientes_atingidos": clientes_atingidos,
        "total_compras_realizadas": total_compras,
    }

    return jsonify(relatorio)

def to_dict(item):
    return {
        **item,
        "_id": str(item["_id"]),
        "customer": str(item["customer"]),
        "order_total": float(item.get("order_total", 0)),
        "date": item["date"].isoformat(),
        "status": str(item["status"])
    }

@dashboard.route('/order/top3/<string:period>', methods=['GET'])
def get_top_3(period):
    hoje = datetime.now()
    
    # Determinar o intervalo de datas baseado no período
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
