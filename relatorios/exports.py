from openpyxl import Workbook
from openpyxl.styles import Font
from django.http import HttpResponse
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors

from .services import pontuacao_por_secao


from .services import pontuacao_por_secao


def exportar_pontuacao_excel(secao, data_inicio=None, data_fim=None):
    dados = pontuacao_por_secao(
        secao=secao,
        data_inicio=data_inicio,
        data_fim=data_fim,
    )

    wb = Workbook()
    ws = wb.active
    ws.title = "Pontuação"

    # Cabeçalho
    ws.append(["Usuário", "Total de Pontos"])
    for cell in ws[1]:
        cell.font = Font(bold=True)

    # Dados
    for d in dados:
        ws.append([
            d["usuario__username"],
            float(d["total"]),
        ])

    response = HttpResponse(
        content_type=(
            "application/vnd.openxmlformats-"
            "officedocument.spreadsheetml.sheet"
        )
    )
    response["Content-Disposition"] = (
        'attachment; filename="pontuacao_secao.xlsx"'
    )

    wb.save(response)
    return response

def exportar_pontuacao_pdf(secao, data_inicio=None, data_fim=None):
    dados = pontuacao_por_secao(
        secao=secao,
        data_inicio=data_inicio,
        data_fim=data_fim,
    )

    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = (
        'attachment; filename="pontuacao_secao.pdf"'
    )

    doc = SimpleDocTemplate(
        response,
        pagesize=A4,
        rightMargin=40,
        leftMargin=40,
        topMargin=40,
        bottomMargin=40,
    )

    styles = getSampleStyleSheet()
    elementos = []

    # Título
    elementos.append(
        Paragraph("Relatório de Pontuação da Seção", styles["Title"])
    )

    if data_inicio and data_fim:
        elementos.append(
            Paragraph(
                f"Período: {data_inicio} até {data_fim}",
                styles["Normal"],
            )
        )

    elementos.append(Paragraph("<br/>", styles["Normal"]))

    # Tabela
    tabela_dados = [["Usuário", "Total de Pontos"]]

    for d in dados:
        tabela_dados.append([
            d["usuario__username"],
            str(d["total"]),
        ])

    tabela = Table(tabela_dados, colWidths=[250, 100])
    tabela.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("GRID", (0, 0), (-1, -1), 1, colors.black),
            ("ALIGN", (1, 1), (-1, -1), "CENTER"),
        ])
    )

    elementos.append(tabela)

    doc.build(elementos)
    return response
