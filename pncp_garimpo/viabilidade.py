# -*- coding: utf-8 -*-
"""
Camada 2 — Estimador de viabilidade.

Para os editais favoráveis do radar (Camada 1), cruza o HISTÓRICO de contratos
firmados (`/v1/contratos`) do MESMO órgão para estimar:
  - quão pulverizado vs. concentrado é o mercado daquele órgão (barreira de entrada);
  - quem são os vencedores recorrentes (incumbentes);
  - um preço-alvo estimado para ganhar e se ainda sobra margem;
  - (opcional) se algum incumbente está impedido no CEIS/CNEP.

LIMITAÇÕES HONESTAS (leia antes de confiar nos números):
  * A API de contratos expõe o VENCEDOR e o VALOR, mas NÃO o número de licitantes
    que disputaram. Logo, "concorrência provável" é estimada pela DIVERSIDADE de
    fornecedores que já ganharam no órgão — um proxy, não a contagem real.
  * O histórico sob a Lei 14.133 é curto (obrigatoriedade plena desde ~2024),
    então há pouco lastro estatístico. Trate como indício, não como verdade.
  * Exigências de habilitação que eliminam um fornecedor estão no PDF do edital,
    fora dos campos estruturados. Não entram neste cálculo.

Tudo aqui é ESTIMATIVA, não garantia de vitória.

Uso:
    python3 viabilidade.py            # usa o CSV do radar (top N)
    python3 viabilidade.py --top 8    # analisa os 8 melhores
    python3 viabilidade.py --debug    # imprime JSON real de um contrato
"""

import csv
import os
import statistics
import sys
import unicodedata
from datetime import date, timedelta

import config
import pncp_api as api


def _normalizar(texto):
    if not texto:
        return ""
    s = unicodedata.normalize("NFKD", texto)
    return "".join(c for c in s if not unicodedata.combining(c)).lower()


# ---------------------------------------------------------------------------
# Coleta de histórico de contratos do órgão
# ---------------------------------------------------------------------------

def buscar_contratos_orgao(cnpj_orgao, meses, debug=False):
    """
    Puxa contratos firmados pelo órgão nos últimos `meses`, paginando.

    /v1/contratos exige janela de datas (dataInicial/dataFinal, yyyymmdd) e
    aceita cnpjOrgao para filtrar por órgão — validado em runtime.
    """
    if not cnpj_orgao:
        return []
    hoje = date.today()
    inicial = (hoje - timedelta(days=int(meses * 30.5))).strftime("%Y%m%d")
    final = hoje.strftime("%Y%m%d")
    params = {"dataInicial": inicial, "dataFinal": final, "cnpjOrgao": cnpj_orgao}

    contratos = []
    introspeccionado = False
    for item in api.paginar("/v1/contratos", params,
                            max_paginas=config.VIABILIDADE_MAX_PAGINAS):
        if debug and not introspeccionado:
            api.introspeccionar(item, "CONTRATO (formato real)")
            introspeccionado = True
        contratos.append(item)
    return contratos


def filtrar_similares(contratos, palavras_chave):
    """Mantém só contratos cujo objetoContrato casa com alguma palavra-chave."""
    palavras = [_normalizar(p) for p in palavras_chave if p]
    similares = []
    for c in contratos:
        obj = _normalizar(api.pegar(c, "objetoContrato", ""))
        if any(p in obj for p in palavras):
            similares.append(c)
    return similares


# ---------------------------------------------------------------------------
# Estatísticas do mercado do órgão
# ---------------------------------------------------------------------------

def _valor_contrato(c):
    """Valor do contrato, preferindo global; cai para inicial; ignora zeros/None."""
    for campo in ("valorGlobal", "valorInicial", "valorAcumulado"):
        v = api.pegar(c, campo)
        if isinstance(v, (int, float)) and v > 0:
            return float(v)
    return None


def estatisticas(similares):
    """
    Resume o histórico similar: nº, valores (mediana/min/max), fornecedores
    distintos, concentração do líder e lista de vencedores recorrentes.
    """
    valores = [v for v in (_valor_contrato(c) for c in similares) if v]
    fornecedores = {}
    for c in similares:
        nome = api.pegar(c, "nomeRazaoSocialFornecedor", "(sem nome)")
        ni = api.pegar(c, "niFornecedor", "")
        chave = ni or nome
        fornecedores.setdefault(chave, {"nome": nome, "ni": ni, "qtd": 0, "total": 0.0})
        fornecedores[chave]["qtd"] += 1
        v = _valor_contrato(c)
        if v:
            fornecedores[chave]["total"] += v

    n_contratos = len(similares)
    n_fornecedores = len(fornecedores)
    recorrentes = sorted(fornecedores.values(), key=lambda x: x["qtd"], reverse=True)
    top_share = (recorrentes[0]["qtd"] / n_contratos) if n_contratos else 0.0

    return {
        "n_contratos": n_contratos,
        "n_fornecedores": n_fornecedores,
        "valor_mediano": statistics.median(valores) if valores else None,
        "valor_min": min(valores) if valores else None,
        "valor_max": max(valores) if valores else None,
        "concentracao_top": top_share,         # 0..1 — fatia do fornecedor líder
        "recorrentes": recorrentes[:5],
        "fornecedores_ni": {f["ni"] for f in fornecedores.values() if f["ni"]},
    }


# ---------------------------------------------------------------------------
# Estimativa de viabilidade
# ---------------------------------------------------------------------------

def estimar_viabilidade(edital, stats, impedidos=None):
    """
    Produz preço-alvo, margem e um score de viabilidade (0-100) com explicação
    textual fator a fator. Reforça que é estimativa.
    """
    impedidos = impedidos or set()
    valor_estimado = float(edital.get("valor_estimado") or 0.0) or None
    explicacao = []
    score = 0
    max_score = 0

    # --- Preço-alvo ---
    # (a) histórico: mediana dos valores vencedores similares (dado real).
    # (b) desconto: estimado do edital menos um desconto típico (palpite).
    preco_hist = stats["valor_mediano"]
    preco_desc = (valor_estimado * (1 - config.DESCONTO_TIPICO_PADRAO)) if valor_estimado else None

    candidatos = [p for p in (preco_hist, preco_desc) if p]
    preco_alvo = min(candidatos) if candidatos else None  # conservador: o menor

    if preco_hist:
        explicacao.append(
            "Preço-alvo por histórico: mediana de R$ {:,.2f} em {} contrato(s) similar(es) do órgão.".format(
                preco_hist, stats["n_contratos"]))
    else:
        explicacao.append(
            "Sem histórico de valores similares no órgão — preço-alvo cai no desconto típico ({}%).".format(
                int(config.DESCONTO_TIPICO_PADRAO * 100)))
    if preco_desc:
        explicacao.append(
            "Preço-alvo por desconto típico sobre o estimado: R$ {:,.2f}.".format(preco_desc))

    # --- Margem vs. teto de execução do usuário ---
    max_score += 30
    if preco_alvo and preco_alvo <= config.VALOR_MAXIMO:
        folga = config.VALOR_MAXIMO - preco_alvo
        score += 30
        explicacao.append(
            "Preço-alvo (R$ {:,.2f}) cabe no seu teto (R$ {:,.2f}); folga de R$ {:,.2f}.".format(
                preco_alvo, config.VALOR_MAXIMO, folga))
    elif preco_alvo:
        explicacao.append(
            "Preço-alvo (R$ {:,.2f}) ESTOURA o seu teto (R$ {:,.2f}) — margem apertada.".format(
                preco_alvo, config.VALOR_MAXIMO))

    # --- Pulverização do mercado (proxy de concorrência) ---
    max_score += 40
    conc = stats["concentracao_top"]
    nf = stats["n_fornecedores"]
    if stats["n_contratos"] == 0:
        explicacao.append(
            "Nenhum contrato similar no histórico do órgão: mercado novo/incerto. "
            "Pouco lastro para estimar concorrência (limitação conhecida).")
    elif conc >= 0.6:
        score += 8
        explicacao.append(
            "Mercado CONCENTRADO: o líder ficou com {:.0f}% dos contratos similares "
            "({} fornecedor(es) no total). Incumbente forte = entrada mais difícil.".format(
                conc * 100, nf))
    elif conc >= 0.35:
        score += 24
        explicacao.append(
            "Mercado MODERADAMENTE disputado: líder com {:.0f}%, {} fornecedores. "
            "Há espaço, mas existe um nome recorrente.".format(conc * 100, nf))
    else:
        score += 40
        explicacao.append(
            "Mercado PULVERIZADO: líder com só {:.0f}%, {} fornecedores distintos. "
            "Boa brecha para um entrante.".format(conc * 100, nf))

    # --- Lastro histórico ---
    max_score += 20
    if stats["n_contratos"] >= 8:
        score += 20
        explicacao.append("Lastro razoável: {} contratos similares dão alguma confiança.".format(
            stats["n_contratos"]))
    elif stats["n_contratos"] >= 3:
        score += 10
        explicacao.append("Lastro fraco: {} contratos — leia como indício.".format(stats["n_contratos"]))
    else:
        explicacao.append("Lastro mínimo: base histórica curta sob a Lei 14.133. Cuidado.")

    # --- Incumbente impedido (CEIS/CNEP) — brecha ---
    max_score += 10
    incumbente_impedido = stats["fornecedores_ni"] & impedidos
    if incumbente_impedido:
        score += 10
        explicacao.append(
            "BRECHA: incumbente(s) impedido(s) no CEIS/CNEP ({}). Pode abrir espaço.".format(
                ", ".join(incumbente_impedido)))
    elif impedidos is not None and config.PORTAL_TRANSPARENCIA_API_KEY:
        explicacao.append("Nenhum incumbente impedido encontrado no CEIS/CNEP.")

    # Normaliza para 0..100
    score_norm = round((score / max_score) * 100) if max_score else 0

    return {
        "score_viabilidade": score_norm,
        "preco_alvo": preco_alvo,
        "preco_alvo_historico": preco_hist,
        "preco_alvo_desconto": preco_desc,
        "n_contratos_similares": stats["n_contratos"],
        "n_fornecedores": stats["n_fornecedores"],
        "concentracao_top_pct": round(stats["concentracao_top"] * 100, 1),
        "vencedores_recorrentes": "; ".join(
            "{} ({}x)".format(r["nome"], r["qtd"]) for r in stats["recorrentes"]),
        "explicacao": " ".join(explicacao),
    }


# ---------------------------------------------------------------------------
# CEIS/CNEP (opcional)
# ---------------------------------------------------------------------------

def carregar_impedidos(cnpjs_fornecedores):
    """
    (Opcional) Consulta CEIS/CNEP no Portal da Transparência se houver chave.

    Sem chave de API, devolve conjunto vazio com aviso — sem quebrar o fluxo.
    Mantido simples de propósito; extração robusta fica como melhoria futura.
    """
    chave = config.PORTAL_TRANSPARENCIA_API_KEY or os.environ.get(
        "PORTAL_TRANSPARENCIA_API_KEY", "")
    if not chave:
        print("CEIS/CNEP: pulado (sem PORTAL_TRANSPARENCIA_API_KEY). "
              "Checagem de incumbente impedido desativada.")
        return set()
    # Implementação enxuta: consulta por CNPJ no endpoint CEIS.
    import urllib.request
    import json as _json
    impedidos = set()
    base = "https://api.portaldatransparencia.gov.br/api-de-dados/ceis"
    for ni in cnpjs_fornecedores:
        try:
            url = "{}?codigoSancionado={}&pagina=1".format(base, ni)
            req = urllib.request.Request(url, headers={
                "Accept": "application/json", "chave-api-dados": chave})
            with urllib.request.urlopen(req, timeout=config.TIMEOUT) as r:
                dados = _json.loads(r.read().decode("utf-8"))
                if dados:
                    impedidos.add(ni)
        except Exception:
            continue
    return impedidos


# ---------------------------------------------------------------------------
# Leitura do radar + main
# ---------------------------------------------------------------------------

def ler_radar(caminho):
    if not os.path.exists(caminho):
        print("CSV do radar não encontrado ({}). Rode antes: python3 radar.py".format(caminho))
        sys.exit(1)
    with open(caminho, "r", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def imprimir(edital, via):
    print("\n" + "-" * 70)
    print("{} — {}/{}".format(edital["orgao"], edital["municipio"], edital["uf"]))
    print("Objeto: {}".format((edital["objeto"] or "")[:120]))
    print("Valor estimado do edital: R$ {:,.2f} | encerra {}".format(
        float(edital.get("valor_estimado") or 0), edital.get("encerramento", "")))
    print(">> SCORE DE VIABILIDADE (estimativa): {}/100".format(via["score_viabilidade"]))
    if via["preco_alvo"]:
        print("   Preço-alvo estimado: R$ {:,.2f}".format(via["preco_alvo"]))
    print("   Concorrência (proxy): {} fornecedores distintos, líder com {}%".format(
        via["n_fornecedores"], via["concentracao_top_pct"]))
    if via["vencedores_recorrentes"]:
        print("   Recorrentes: {}".format(via["vencedores_recorrentes"]))
    print("   Por quê: {}".format(via["explicacao"]))


def salvar_csv(linhas, caminho):
    if not linhas:
        return
    campos = list(linhas[0].keys())
    with open(caminho, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=campos)
        w.writeheader()
        w.writerows(linhas)
    print("\nCSV salvo em: {}".format(caminho))


def main(argv):
    debug = "--debug" in argv
    top = 5
    if "--top" in argv:
        try:
            top = int(argv[argv.index("--top") + 1])
        except (ValueError, IndexError):
            pass

    ok, msg = api.testar_conectividade()
    print(msg)
    if not ok:
        sys.exit(2)

    print("\nLEMBRETE: viabilidade é ESTIMATIVA, não garantia. A API mostra o")
    print("vencedor e o valor, mas NÃO quantos licitantes disputaram — concorrência")
    print("aqui é um proxy pela diversidade de fornecedores. Habilitação está no PDF.\n")

    editais = ler_radar(config.CSV_RADAR)[:top]
    print("Analisando os {} editais mais favoráveis do radar...".format(len(editais)))

    saida = []
    for ed in editais:
        cnpj = ed.get("cnpj_orgao", "")
        palavras = [p.strip() for p in (ed.get("palavras_casadas") or "").split(";") if p.strip()]
        if not palavras:
            palavras = config.PALAVRAS_CHAVE
        contratos = buscar_contratos_orgao(cnpj, config.VIABILIDADE_MESES_HISTORICO, debug=debug)
        debug = False  # introspecção só uma vez
        similares = filtrar_similares(contratos, palavras)
        stats = estatisticas(similares)
        impedidos = carregar_impedidos(stats["fornecedores_ni"]) if stats["fornecedores_ni"] else set()
        via = estimar_viabilidade(ed, stats, impedidos)
        imprimir(ed, via)
        linha = {
            "score_viabilidade": via["score_viabilidade"],
            "orgao": ed["orgao"], "municipio": ed["municipio"], "uf": ed["uf"],
            "objeto": ed["objeto"], "valor_estimado": ed["valor_estimado"],
            "preco_alvo": via["preco_alvo"],
            "preco_alvo_historico": via["preco_alvo_historico"],
            "preco_alvo_desconto": via["preco_alvo_desconto"],
            "n_contratos_similares": via["n_contratos_similares"],
            "n_fornecedores": via["n_fornecedores"],
            "concentracao_top_pct": via["concentracao_top_pct"],
            "vencedores_recorrentes": via["vencedores_recorrentes"],
            "encerramento": ed.get("encerramento", ""),
            "link_edital": ed.get("link_edital", ""),
            "explicacao": via["explicacao"],
        }
        saida.append(linha)

    saida.sort(key=lambda x: x["score_viabilidade"], reverse=True)
    salvar_csv(saida, config.CSV_VIABILIDADE)


if __name__ == "__main__":
    main(sys.argv[1:])
