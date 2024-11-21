from flask import Blueprint, jsonify, send_file
from datetime import datetime, timedelta
from connections import db
from bson.decimal128 import Decimal128
from bson import ObjectId
import bson
import io
from fpdf import FPDF

# Definindo o Blueprint
dashboard = Blueprint("dashboard", __name__)

# Coleções
order_collection = db['orders']
client_collection = db['users']

def calculate_order_total(order):
    total = 0
    for item in order.get('items', []):
        price = item.get('price', 0)
        qty = item.get('qty', 0)

        # Converte Decimal128 para float, se necessário
        if isinstance(price, Decimal128):
            price = float(price.to_decimal())

        total += price * qty

    return round(total, 2)

def to_dict(order):
    customer_data = order.get("customer", {})
    order_total = order.get("order_total", 0)
    
    # Converte order_total se for Decimal128
    if isinstance(order_total, Decimal128):
        order_total = float(order_total.to_decimal())

    return {
        "_id": str(order.get("_id")),  # Converte ObjectId para string
        "customer_id": str(customer_data.get("_id", "")) if "_id" in customer_data else "",
        "customer_name": customer_data.get("name", ""),
        "order_total": round(order_total, 2),
        "date": order.get("date").isoformat() if order.get("date") else "",
        "status": order.get("status", "")
    }

# Função para serializar dados JSON de maneira segura
def serialize_document(doc):
    """Converte um documento MongoDB em um dicionário serializável."""
    if isinstance(doc, list):
        return [serialize_document(item) for item in doc]
    elif isinstance(doc, dict):
        return {key: serialize_document(value) for key, value in doc.items()}
    elif isinstance(doc, ObjectId):
        return str(doc)
    elif isinstance(doc, Decimal128):
        return float(doc.to_decimal())
    elif isinstance(doc, datetime):
        return doc.isoformat()
    else:
        return doc

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

    # Clientes atingidos
    clientes_atingidos = set(order.get('customer', {}).get('_id') for order in vendas_do_mes)

    # Compras realizadas
    total_compras = len(vendas_do_mes)

    # Vendas do mês anterior
    vendas_ultimo_mes = list(order_collection.find({
        "date": {"$gte": primeiro_dia_ultimo_mes, "$lt": primeiro_dia_do_mes}
    }))
    total_vendas_ultimo_mes = sum(calculate_order_total(order) for order in vendas_ultimo_mes)

    # Aumento percentual
    aumento_em_porcentagem = 0.0
    if total_vendas_ultimo_mes > 0:
        aumento_em_porcentagem = ((total_vendas - total_vendas_ultimo_mes) / total_vendas_ultimo_mes) * 100

    relatorio = {
        "total_vendas": total_vendas,
        "aumento_em_porcentagem": aumento_em_porcentagem,
        "clientes_atingidos": len(clientes_atingidos),
        "total_compras_realizadas": total_compras,
    }

    return jsonify(serialize_document(relatorio))

@dashboard.route('/order/top3/<string:period>', methods=['GET'])
def get_top_3(period):
    hoje = datetime.now()

    # Definindo o intervalo de datas
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
        {"$match": {"date": {"$gte": start_date, "$lt": end_date}}},
        {"$addFields": {"order_total": {
            "$sum": {"$map": {
                "input": {"$cond": {"if": {"$isArray": "$items"}, "then": "$items", "else": []}},
                "as": "item",
                "in": {"$multiply": ["$$item.price", "$$item.qty"]}
            }}
        }}},
        {"$sort": {"order_total": -1}},
        {"$limit": 3},
        {
            "$lookup": {
                "from": "users",  # Nome da coleção de clientes
                "localField": "customer_id",  # Campo local em orders
                "foreignField": "_id",  # Campo correspondente em users
                "as": "customer_info"
            }
        },
        {
            "$addFields": {
                "customer_name": {"$arrayElemAt": ["$customer_info.name", 0]},  # Nome do cliente
                "seller_name": {"$arrayElemAt": ["$customer_info.surname", 0]}  # Nome do vendedor ou outro campo caso se aplique
            }
        },
        {"$project": {"customer_info": 0}}
    ]

    top_orders = list(order_collection.aggregate(top_orders_pipeline))
    return jsonify(serialize_document(top_orders)), 200


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
                    "$multiply": [
                        {"$toDouble": "$items.price"},  # Converte para double
                        "$items.qty"
                    ]
                }
            }
        }
    },
    {"$sort": {"_id.month": 1}}
]


    monthly_sales_data = list(order_collection.aggregate(monthly_sales_pipeline))

    sales = {
        month["_id"]["month"]: float(month.get("total_sales", 0))
        for month in monthly_sales_data
    }
    return jsonify(sales)

@dashboard.route('/backup', methods=['GET'])
def backup_data():
    try:
        sales_data = list(order_collection.find())
        products_data = list(db['products'].find())
        backup_content = {
            'sales': sales_data,
            'products': products_data
        }
        bson_data = bson.encode(backup_content)
        return send_file(
            io.BytesIO(bson_data),
            mimetype='application/octet-stream',
            as_attachment=True,
            download_name='backup_dados.bson'
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500

import tempfile
import os

@dashboard.route('/export', methods=['GET'])
def export_data():
    try:
        # Buscar dados de pedidos
        orders = list(order_collection.find())

        if not orders:
            raise ValueError("Nenhuma venda encontrada para exportar.")

        # Criar o PDF
        pdf = FPDF()
        pdf.set_auto_page_break(auto=True, margin=15)
        pdf.add_page()
        pdf.set_font('Arial', size=12)
        pdf.cell(200, 10, txt="Relatório de Vendas", ln=True, align='C')

        for order in orders:
            order_total = calculate_order_total(order)
            pdf.ln(10)
            pdf.cell(0, 10, f"ID: {order.get('_id', '')}", ln=True)
            pdf.cell(0, 10, f"Cliente: {order.get('customer', {}).get('name', 'Não informado')}", ln=True)
            pdf.cell(0, 10, f"Data: {order.get('date').strftime('%d/%m/%Y') if order.get('date') else 'Não informado'}", ln=True)
            pdf.cell(0, 10, f"Total: R$ {order_total:.2f}", ln=True)

        # Criar um arquivo temporário
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_file:
            pdf.output(temp_file.name)
            temp_file_path = temp_file.name

        # Enviar o arquivo para o cliente
        return send_file(
            temp_file_path,
            mimetype='application/pdf',
            as_attachment=True,
            download_name='relatorio_vendas.pdf'
        )
    except Exception as e:
        print(f"Erro ao exportar dados: {str(e)}")
        return jsonify({"error": str(e)}), 500
    finally:
        # Remover o arquivo temporário após o envio
        try:
            if 'temp_file_path' in locals() and os.path.exists(temp_file_path):
                os.remove(temp_file_path)
        except Exception as cleanup_error:
            print(f"Erro ao limpar arquivo temporário: {cleanup_error}")
