# -*- coding: utf-8 -*-
"""
Detalhamento de itens — preço unitário e quantidade por edital.

A coluna "valor" do radar é o TOTAL estimado da compra, que pode reunir vários
itens. Este script desce ao nível de item para mostrar, de cada edital favorável:
descrição, quantidade, unidade e PREÇO UNITÁRIO estimado — pra você ter ideia
"por quanto dá pra comprar/fornecer" e comparar com o seu custo.

IMPORTANTE: o "valorUnitarioEstimado" é a ESTIMATIVA do órgão (preço de
referência), NÃO o preço final. Na disputa o vencedor costuma fechar abaixo
disso. É um ponto de partida, não um preço garantido.

Uso:
    python3 itens.py            # detalha os 10 melhores editais do radar
    python3 itens.py --top 20   # detalha os 20 melhores
"""

import csv
import sys

import config
import pncp_api as api


def _moeda(v):
    try:
        return "R$ {:,.2f}".format(float(v))
    except (TypeError, ValueError):
        return "-"


def detalhar_itens(edital):
    """Busca e normaliza os itens de um edital a partir do numeroControlePNCP."""
    itens = api.buscar_itens_edital(edital.get("numero_controle", ""))
    linhas = []
    for it in itens:
        sigiloso = api.pegar(it, "orcamentoSigiloso", False)
        descricao = api.corrigir_texto(api.pegar(it, "descricao", "") or "")
        linhas.append({
            "item": api.pegar(it, "numeroItem", ""),
            "descricao": " ".join(descricao.split()),
            "quantidade": api.pegar(it, "quantidade", ""),
            "unidade": api.pegar(it, "unidadeMedida", ""),
            "preco_unitario": None if sigiloso else api.pegar(it, "valorUnitarioEstimado"),
            "total": None if sigiloso else api.pegar(it, "valorTotal"),
            "beneficio": api.pegar(it, "tipoBeneficioNome", ""),
            "sigiloso": sigiloso,
        })
    return linhas


def imprimir(edital, itens):
    print("\n" + "=" * 78)
    print("{} — {}/{}".format(edital["orgao"], edital["municipio"], edital["uf"]))
    print("Compra: {}".format(api.corrigir_texto(edital.get("objeto") or "")))
    print("Total estimado: {} | encerra {} | {}".format(
        _moeda(edital.get("valor_estimado")), edital.get("encerramento", ""),
        edital.get("link_edital", "")))
    if not itens:
        print("  (sem itens estruturados disponíveis para este edital)")
        return
    print("-" * 78)
    # Descrição COMPLETA de cada item (pra você pesquisar o preço), seguida de
    # quantidade, unidade, preço unitário e total estimados.
    for it in itens:
        qtd_un = "{:g} {}".format(float(it["quantidade"]), it["unidade"]) \
            if str(it["quantidade"]).strip() not in ("", "None") else "-"
        preco = "(sigiloso)" if it["sigiloso"] else _moeda(it["preco_unitario"])
        total = "" if it["sigiloso"] else "  (total {})".format(_moeda(it["total"]))
        benef = ""
        if it["beneficio"] and it["beneficio"] not in ("Não se aplica", ""):
            benef = "  [{}]".format(it["beneficio"])
        print("\n  [item {}] {}".format(it["item"], it["descricao"]))
        print("           {} × {}{}{}".format(qtd_un, preco, total, benef))


def salvar_csv(linhas, caminho):
    if not linhas:
        return
    campos = ["orgao", "municipio", "uf", "objeto_compra", "item", "descricao",
              "quantidade", "unidade", "preco_unitario_estimado", "total_estimado",
              "beneficio", "encerramento", "link_edital"]
    with open(caminho, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=campos)
        w.writeheader()
        w.writerows(linhas)
    print("\nCSV salvo em: {}".format(caminho))


def main(argv):
    top = 10
    if "--top" in argv:
        try:
            top = int(argv[argv.index("--top") + 1])
        except (ValueError, IndexError):
            pass

    ok, msg = api.testar_conectividade()
    print(msg)
    if not ok:
        sys.exit(2)

    print("\nLEMBRETE: preço unitário é ESTIMATIVA do órgão (referência), não preço")
    print("final. Na disputa o vencedor costuma fechar abaixo disso.\n")

    import os
    if not os.path.exists(config.CSV_RADAR):
        print("Rode antes: python3 radar.py"); sys.exit(1)
    with open(config.CSV_RADAR, "r", encoding="utf-8-sig") as f:
        editais = list(csv.DictReader(f))[:top]

    print("Detalhando itens dos {} editais mais favoráveis...".format(len(editais)))
    saida = []
    for ed in editais:
        try:
            ed["valor_estimado"] = float(ed.get("valor_estimado") or 0)
        except ValueError:
            ed["valor_estimado"] = 0.0
        itens = detalhar_itens(ed)
        imprimir(ed, itens)
        for it in itens:
            saida.append({
                "orgao": ed["orgao"], "municipio": ed["municipio"], "uf": ed["uf"],
                "objeto_compra": api.corrigir_texto(ed.get("objeto") or ""), "item": it["item"],
                "descricao": it["descricao"], "quantidade": it["quantidade"],
                "unidade": it["unidade"],
                "preco_unitario_estimado": "" if it["sigiloso"] else it["preco_unitario"],
                "total_estimado": "" if it["sigiloso"] else it["total"],
                "beneficio": it["beneficio"], "encerramento": ed.get("encerramento", ""),
                "link_edital": ed.get("link_edital", ""),
            })
    salvar_csv(saida, config.CSV_ITENS)


if __name__ == "__main__":
    main(sys.argv[1:])
