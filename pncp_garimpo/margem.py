# -*- coding: utf-8 -*-
"""
Margem líquida com frete — reordena os itens pelo LUCRO REAL, não pelo bruto.

Para cada item (de saida_itens.csv) calcula:
    preço de venda ≈ estimado × (1 − desconto típico da disputa)
    custo          = custo real (custos.csv) OU estimado × CUSTO_PCT_DO_ESTIMADO
    imposto        = venda × IMPOSTO_PCT
    frete total    = FRETE_POR_ENTREGA × nº de entregas (1, ou ENTREGAS_SRP se SRP)
    LUCRO LÍQUIDO  = (venda − custo) × quantidade − imposto − frete total

E sinaliza quando o FRETE come a margem (entrega parcelada distante + item barato).

LEMBRETE: é ESTIMATIVA. O preço de venda assume o desconto mediano do histórico;
o custo, no modo triagem, é um palpite (% do estimado). Para número real, preencha
custos.csv com o seu custo de compra dos itens que te interessam.

Uso:
    python3 margem.py            # usa saida_itens.csv (rode itens.py antes)
    python3 margem.py --top 25   # mostra os 25 mais lucrativos
"""

import csv
import os
import sys
import unicodedata

import config


def _norm(s):
    if not s:
        return ""
    s = unicodedata.normalize("NFKD", s)
    return "".join(c for c in s if not unicodedata.combining(c)).lower()


# Pistas de que a entrega é parcelada (registro de preços) -> frete recorrente.
_PISTAS_SRP = [_norm(x) for x in (
    "registro de preco", "registro de precos", "futura e eventual",
    "eventual aquisicao", "eventual contratacao", "parcelada", "sob demanda",
    "fornecimento continuo", "fornecimento contínuo")]


def carregar_custos():
    """Lê custos.csv (trecho_descricao,custo_unitario). Devolve lista (norm, custo)."""
    caminho = config.ARQUIVO_CUSTOS
    if not os.path.exists(caminho):
        return []
    custos = []
    with open(caminho, "r", encoding="utf-8-sig") as f:
        for linha in csv.reader(f):
            if len(linha) < 2:
                continue
            trecho, valor = linha[0].strip(), linha[1].strip()
            if not trecho or _norm(trecho) == "trecho_descricao":
                continue
            try:
                custos.append((_norm(trecho), float(valor.replace(",", "."))))
            except ValueError:
                continue
    return custos


def custo_do_item(descricao, estimado, tabela_custos):
    """Custo real (se casar em custos.csv) ou palpite (% do estimado). (custo, fonte)."""
    dnorm = _norm(descricao)
    for trecho, valor in tabela_custos:
        if trecho and trecho in dnorm:
            return valor, "real"
    return estimado * config.CUSTO_PCT_DO_ESTIMADO, "estimado"


def eh_srp(objeto):
    o = _norm(objeto)
    return any(p in o for p in _PISTAS_SRP)


def _num(x):
    try:
        return float(str(x).replace(",", "."))
    except (ValueError, AttributeError):
        return None


def calcular(itens, tabela_custos):
    linhas = []
    for it in itens:
        estimado = _num(it.get("preco_unitario_estimado"))
        qtd = _num(it.get("quantidade"))
        if not estimado or estimado <= 0 or not qtd or qtd <= 0:
            continue  # sigiloso/sem dado: não dá pra calcular

        venda = estimado * (1 - config.DESCONTO_DISPUTA_PCT)
        custo, fonte = custo_do_item(it.get("descricao", ""), estimado, tabela_custos)
        srp = eh_srp(it.get("objeto_compra", ""))
        n_entregas = config.ENTREGAS_SRP if srp else 1
        frete_total = config.FRETE_POR_ENTREGA * n_entregas

        venda_total = venda * qtd
        imposto = venda_total * config.IMPOSTO_PCT
        lucro_bruto = (venda - custo) * qtd
        lucro_liquido = lucro_bruto - imposto - frete_total
        margem_pct = (lucro_liquido / venda_total * 100) if venda_total else 0.0
        frete_pct = (frete_total / venda_total * 100) if venda_total else 0.0

        linhas.append({
            "lucro_liquido": round(lucro_liquido, 2),
            "margem_pct": round(margem_pct, 1),
            "municipio": it.get("municipio", ""),
            "uf": it.get("uf", ""),
            "descricao": it.get("descricao", ""),
            "qtd": qtd,
            "unidade": it.get("unidade", ""),
            "estimado_unit": round(estimado, 2),
            "venda_unit": round(venda, 2),
            "custo_unit": round(custo, 2),
            "custo_fonte": fonte,
            "imposto": round(imposto, 2),
            "srp": "SRP" if srp else "única",
            "n_entregas": n_entregas,
            "frete_total": round(frete_total, 2),
            "frete_pct": round(frete_pct, 1),
            "encerra": (it.get("encerramento", "") or "").split("T")[0],
            "link": it.get("link_edital", ""),
        })
    linhas.sort(key=lambda x: x["lucro_liquido"], reverse=True)
    return linhas


def _trim(s, n=40):
    s = " ".join((s or "").split())
    return s if len(s) <= n else s[:n].rstrip() + "…"


def imprimir(linhas, top):
    print("\n" + "=" * 104)
    print("MARGEM LÍQUIDA por item — base {}/{} (venda = estimado −{:.0f}% | imposto {:.0f}% | "
          "frete R${:.0f}/entrega)".format(
              config.BASE_CIDADE, config.BASE_UF, config.DESCONTO_DISPUTA_PCT * 100,
              config.IMPOSTO_PCT * 100, config.FRETE_POR_ENTREGA))
    print("=" * 104)
    print("{:>11} {:>6} {:<26} {:<16} {:>8} {:>8} {:>7} {:>9}".format(
        "LUCRO LÍQ.", "MARG%", "ITEM", "LOCAL", "VENDA", "CUSTO", "FRETE%", "ENTREGA"))
    print("-" * 104)
    for l in linhas[:top]:
        flag = "❌" if l["lucro_liquido"] <= 0 else ("⚠️" if l["frete_pct"] > config.FRETE_PCT_MAXIMO * 100 else "✅")
        print("{} R${:>9,.0f} {:>5.0f}% {:<26} {:<16} {:>8.2f} {:>8.2f} {:>6.0f}% {:>4}x{:<4}".format(
            flag, l["lucro_liquido"], l["margem_pct"], _trim(l["descricao"], 26),
            "{}/{}".format(l["municipio"], l["uf"])[:16], l["venda_unit"], l["custo_unit"],
            l["frete_pct"], l["n_entregas"], l["srp"]))


def salvar_csv(linhas, caminho="saida_margem.csv"):
    if not linhas:
        return
    campos = ["lucro_liquido", "margem_pct", "municipio", "uf", "descricao", "qtd",
              "unidade", "estimado_unit", "venda_unit", "custo_unit", "custo_fonte",
              "imposto", "srp", "n_entregas", "frete_total", "frete_pct", "encerra", "link"]
    with open(caminho, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=campos)
        w.writeheader()
        w.writerows(linhas)
    print("\nCSV salvo em: {}".format(caminho))


def main(argv):
    top = 25
    if "--top" in argv:
        try:
            top = int(argv[argv.index("--top") + 1])
        except (ValueError, IndexError):
            pass

    fonte = "saida_itens.csv"
    if not os.path.exists(fonte):
        print("Rode antes: python3 itens.py   (gera {})".format(fonte))
        sys.exit(1)
    with open(fonte, "r", encoding="utf-8-sig") as f:
        itens = list(csv.DictReader(f))

    tabela_custos = carregar_custos()
    modo = "PRECISO ({} custos reais em {})".format(len(tabela_custos), config.ARQUIVO_CUSTOS) \
        if tabela_custos else "TRIAGEM (custo = {:.0f}% do estimado — preencha {} para precisão)".format(
            config.CUSTO_PCT_DO_ESTIMADO * 100, config.ARQUIVO_CUSTOS)
    print("Modo: {}".format(modo))

    linhas = calcular(itens, tabela_custos)
    if not linhas:
        print("Nenhum item com valor estimado para calcular (todos sigilosos?).")
        return

    imprimir(linhas, top)
    pos = [l for l in linhas if l["lucro_liquido"] > 0]
    neg = [l for l in linhas if l["lucro_liquido"] <= 0]
    print("-" * 104)
    print("{} itens com lucro líquido positivo, {} no prejuízo (frete/disputa).".format(
        len(pos), len(neg)))
    srp_neg = sum(1 for l in neg if l["srp"] == "SRP")
    print("Dos no prejuízo, {} são entrega PARCELADA (SRP) — o frete recorrente é o que derruba.".format(srp_neg))
    salvar_csv(linhas)


if __name__ == "__main__":
    main(sys.argv[1:])
