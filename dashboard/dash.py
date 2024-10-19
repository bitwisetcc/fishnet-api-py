from flask import Blueprint, jsonify
from datetime import datetime, timedelta
from connections import db

# Definindo o Blueprint
dashboard = Blueprint("dashboard", __name__)

# Coleções
order_collection = db["order"]


# Rota para relatório mensal
@dashboard.route("/order", methods=["GET"])
def order():
    hoje = datetime.now()
    primeiro_dia_do_mes = hoje.replace(day=1)
    ultimo_mes = primeiro_dia_do_mes - timedelta(days=1)
    primeiro_dia_ultimo_mes = ultimo_mes.replace(day=1)

    # Vendas do mês atual
    vendas_do_mes = list(order_collection.find({"date": {"$gte": primeiro_dia_do_mes}}))
    total_vendas = sum(float(order["order_total"].to_decimal()) for order in vendas_do_mes)

    # Clientes atingidos (clientes que fizeram pedidos este mês)
    clientes_atingidos = set(order["id_customer"] for order in vendas_do_mes)

    # Compras realizadas (total de pedidos)
    total_compras = len(vendas_do_mes)

    # Vendas do mês anterior
    vendas_ultimo_mes = list(
        order_collection.find(
            {"date": {"$gte": primeiro_dia_ultimo_mes, "$lt": primeiro_dia_do_mes}}
        )
    )
    total_vendas_ultimo_mes = sum(float(order["order_total"].to_decimal()) for order in vendas_ultimo_mes)

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
        "clientes_atingidos": len(clientes_atingidos),
        "total_compras_realizadas": total_compras,
    }

    return jsonify(relatorio)
