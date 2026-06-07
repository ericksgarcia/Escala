# -*- coding: utf-8 -*-
"""
Camada 1 — Radar de oportunidades.

Puxa as contratações com PROPOSTA EM ABERTO no PNCP (paginando, filtrando por UF),
filtra por palavras-chave e teto de valor, e PONTUA cada edital por "favorabilidade"
para um fornecedor pequeno.

A pontuação é uma HEURÍSTICA TRANSPARENTE — cada ponto vem com um "sinal" textual
que explica de onde saiu. NÃO é probabilidade de vitória nem garantia de nada.
É um ranking de "onde vale a pena olhar primeiro".

Uso:
    python3 radar.py            # roda o radar e salva CSV
    python3 radar.py --debug    # imprime o JSON real do 1º item (introspecção)
    python3 radar.py --top 30   # mostra os 30 primeiros no terminal
"""

import csv
import sys
import unicodedata
from datetime import date, datetime, timedelta

import config
import pncp_api as api


# ---------------------------------------------------------------------------
# Utilidades de texto
# ---------------------------------------------------------------------------

def _normalizar(texto):
    """Minúsculas + sem acentos, para casar palavras-chave de forma robusta."""
    if not texto:
        return ""
    sem_acento = unicodedata.normalize("NFKD", texto)
    sem_acento = "".join(c for c in sem_acento if not unicodedata.combining(c))
    return sem_acento.lower()


_KEYWORDS_NORM = [_normalizar(k) for k in config.PALAVRAS_CHAVE]


def _casa_palavra_chave(objeto):
    """Devolve a lista de palavras-chave (originais) que aparecem no objeto."""
    obj_norm = _normalizar(objeto)
    achadas = []
    for original, norm in zip(config.PALAVRAS_CHAVE, _KEYWORDS_NORM):
        if norm and norm in obj_norm:
            achadas.append(original)
    return achadas


def _dias_ate(data_iso):
    """Dias entre hoje e uma data ISO ('2026-06-15T11:00:00'). None se inválida."""
    if not data_iso:
        return None
    try:
        dt = datetime.fromisoformat(data_iso)
    except ValueError:
        try:
            dt = datetime.fromisoformat(data_iso.split("T")[0])
        except ValueError:
            return None
    return (dt.date() - date.today()).days


def _link_edital(numero_controle):
    """
    Monta o link público do edital no PNCP a partir do numeroControlePNCP.

    Formato observado: '42498733000148-1-001007/2024'
      -> cnpj=42498733000148, sequencial=1007, ano=2024
      -> https://pncp.gov.br/app/editais/42498733000148/2024/1007
    """
    if not numero_controle:
        return ""
    try:
        esquerda, ano = numero_controle.split("/")
        cnpj, _tipo, sequencial = esquerda.split("-")
        return "https://pncp.gov.br/app/editais/{}/{}/{}".format(
            cnpj, ano, int(sequencial))
    except (ValueError, TypeError):
        return ""


# ---------------------------------------------------------------------------
# Pontuação de favorabilidade (heurística transparente e documentada)
# ---------------------------------------------------------------------------

# Limite legal: até R$ 80.000 a contratação tende a ser EXCLUSIVA para ME/EPP
# (LC 123/2006, art. 48, I), o que reduz a concorrência para fornecedor pequeno.
LIMITE_EXCLUSIVO_ME_EPP = 80000.0


def pontuar(edital):
    """
    Calcula score + lista de sinais para um edital.

    Devolve (score:int, sinais:list[str]). Cada sinal documenta o ponto somado.
    Fatores (todos explicáveis):
      - valor baixo  -> provável exclusivo ME/EPP, menos disputa, cabe no meu teto
      - modalidade ágil (pregão-e / dispensa) -> ciclo curto, menos burocracia
      - prazo suficiente para preparar a proposta
      - registro de preço (SRP) -> fornecimento sob demanda, entrada mais flexível
      - proximidade geográfica (mesma UF)
    """
    sinais = []
    score = 0

    valor = api.pegar(edital, "valorTotalEstimado") or 0.0
    modalidade_id = api.pegar(edital, "modalidadeId")
    modalidade_nome = api.pegar(edital, "modalidadeNome", "")
    srp = api.pegar(edital, "srp", False)
    uf = api.pegar(edital, "unidadeOrgao.ufSigla", "")
    dias = _dias_ate(api.pegar(edital, "dataEncerramentoProposta"))

    # --- Valor ---
    # Valor simbólico (sigiloso/não definido) não conta como "baixo": só marca aviso.
    if 0 < valor < config.VALOR_PISO_CONFIAVEL:
        sinais.append("Valor estimado simbólico/não informado (R$ {:.2f}) — confira no edital".format(valor))
    elif valor <= 0:
        sinais.append("Sem valor estimado divulgado — confira no edital")
    else:
        if valor <= config.VALOR_MAXIMO:
            score += 3
            sinais.append("Cabe no meu teto de execução (R$ {:,.0f})".format(valor))
        if valor <= LIMITE_EXCLUSIVO_ME_EPP:
            score += 2
            sinais.append("Provável exclusivo ME/EPP (≤ R$ 80k, LC 123 art.48)")
        if valor > config.VALOR_MAXIMO:
            score -= 1
            sinais.append("Acima do meu teto de execução")

    # --- Modalidade ---
    if modalidade_id in config.MODALIDADES_AGEIS:
        score += 2
        sinais.append("Modalidade ágil ({})".format(modalidade_nome or modalidade_id))
    if modalidade_id == 8:  # Dispensa: disputa tipicamente menor
        score += 1
        sinais.append("Dispensa: disputa costuma ser menor")

    # --- Modo de disputa (proposta fechada = sem lance ao vivo) ---
    if api.pegar(edital, "modoDisputaId") in config.MODOS_DISPUTA_SEM_LANCE:
        score += 1
        sinais.append("Proposta fechada/sem lance ao vivo ({})".format(
            api.pegar(edital, "modoDisputaNome", "")))

    # --- Prazo ---
    if dias is not None:
        if dias >= config.PRAZO_MINIMO_DIAS:
            score += 2
            sinais.append("Prazo suficiente: {} dias até encerrar".format(dias))
            if dias >= 2 * config.PRAZO_MINIMO_DIAS:
                score += 1
                sinais.append("Prazo folgado (≥ {} dias)".format(2 * config.PRAZO_MINIMO_DIAS))
        else:
            score -= 2
            sinais.append("Prazo curto: só {} dias (mín. {})".format(dias, config.PRAZO_MINIMO_DIAS))

    # --- Registro de preço ---
    if srp:
        score += 1
        sinais.append("Registro de preço (SRP): fornecimento sob demanda")

    # --- Proximidade ---
    if uf and uf.upper() == config.UF.upper():
        score += 1
        sinais.append("Na minha UF ({})".format(uf))

    return score, sinais


# ---------------------------------------------------------------------------
# Coleta
# ---------------------------------------------------------------------------

def coletar_editais_abertos(debug=False, uf=None):
    """
    Varre todas as modalidades configuradas no endpoint de proposta aberta e
    devolve a lista bruta de editais (sem filtro de objeto).

    uf: sigla do estado para filtrar. None = Brasil inteiro (útil para proposta
    fechada, em que não há comparecimento e a localização só afeta o frete).
    """
    data_final = (date.today() + timedelta(days=config.JANELA_DIAS)).strftime("%Y%m%d")
    todos = []
    ja_introspeccionado = False

    print("Coletando editais com proposta aberta — região={}, janela até {}...".format(
        uf or "BRASIL", data_final))

    for cod in config.MODALIDADES:
        params = {
            "dataFinal": data_final,
            "codigoModalidadeContratacao": cod,
            "uf": uf,  # None é descartado pelo cliente -> busca nacional
        }
        antes = len(todos)
        for item in api.paginar("/v1/contratacoes/proposta", params,
                                max_paginas=config.MAX_PAGINAS_POR_MODALIDADE):
            if debug and not ja_introspeccionado:
                api.introspeccionar(item)
                ja_introspeccionado = True
            todos.append(item)
        coletados = len(todos) - antes
        if coletados:
            nome = api.pegar(todos[-1], "modalidadeNome", "modalidade {}".format(cod))
            print("  modalidade {:>2} ({:<22}): {} editais".format(cod, nome, coletados))

    print("Total bruto coletado: {} editais.".format(len(todos)))
    return todos


def filtrar_e_pontuar(editais, so_fechada=False):
    """
    Aplica filtro de palavra-chave + teto e devolve linhas pontuadas e ordenadas.

    so_fechada=True mantém apenas editais SEM lance ao vivo (proposta fechada /
    credenciamento), conforme config.MODOS_DISPUTA_SEM_LANCE.
    """
    linhas = []
    for ed in editais:
        objeto = api.corrigir_texto(api.pegar(ed, "objetoCompra", ""))
        palavras = _casa_palavra_chave(objeto)
        if not palavras:
            continue

        if so_fechada and api.pegar(ed, "modoDisputaId") not in config.MODOS_DISPUTA_SEM_LANCE:
            continue

        valor = api.pegar(ed, "valorTotalEstimado") or 0.0
        if config.DESCARTAR_ACIMA_DO_TETO and valor > config.VALOR_MAXIMO:
            continue

        dias = _dias_ate(api.pegar(ed, "dataEncerramentoProposta"))
        if config.DESCARTAR_PRAZO_CURTO and dias is not None and dias < config.PRAZO_MINIMO_DIAS:
            continue

        score, sinais = pontuar(ed)
        linhas.append({
            "score": score,
            "orgao": api.pegar(ed, "orgaoEntidade.razaoSocial", ""),
            "cnpj_orgao": api.pegar(ed, "orgaoEntidade.cnpj", ""),
            "municipio": api.pegar(ed, "unidadeOrgao.municipioNome", ""),
            "uf": api.pegar(ed, "unidadeOrgao.ufSigla", ""),
            "objeto": objeto,
            "valor_estimado": valor,
            "modalidade": api.pegar(ed, "modalidadeNome", ""),
            "modo_disputa": api.pegar(ed, "modoDisputaNome", ""),
            "encerramento": api.pegar(ed, "dataEncerramentoProposta", ""),
            "dias_para_encerrar": dias if dias is not None else "",
            "palavras_casadas": "; ".join(palavras),
            "sinais": " | ".join(sinais),
            "numero_controle": api.pegar(ed, "numeroControlePNCP", ""),
            "link_edital": _link_edital(api.pegar(ed, "numeroControlePNCP", "")),
        })

    linhas.sort(key=lambda x: x["score"], reverse=True)
    return linhas


def salvar_csv(linhas, caminho):
    """Salva o ranking em CSV (UTF-8 com BOM para abrir bem no Excel)."""
    campos = ["score", "orgao", "municipio", "uf", "objeto", "valor_estimado",
              "modalidade", "modo_disputa", "encerramento", "dias_para_encerrar",
              "palavras_casadas", "sinais", "cnpj_orgao", "numero_controle", "link_edital"]
    with open(caminho, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=campos)
        w.writeheader()
        for linha in linhas:
            w.writerow(linha)
    print("CSV salvo em: {}".format(caminho))


def _dia_mes(data_iso):
    """'2026-06-16T08:00:00' -> '16/06'. Vazio se inválida."""
    try:
        d = datetime.fromisoformat((data_iso or "").split("T")[0])
        return d.strftime("%d/%m")
    except ValueError:
        return ""


def imprimir_resumo(linhas, top=30, regiao=None):
    """
    Resumo enxuto: o que estão comprando + valor + encerramento, em tabela
    compacta, mais o PREÇO MÉDIO/MEDIANO dos editais abertos (ignorando valores
    simbólicos/sigilosos abaixo do piso confiável).
    """
    reais = [l["valor_estimado"] for l in linhas
             if l["valor_estimado"] and l["valor_estimado"] >= config.VALOR_PISO_CONFIAVEL]
    n_simbolicos = len(linhas) - len(reais)

    print("\n" + "=" * 78)
    print("RESUMO — {} editais abertos em {} (objeto + teto R$ {:,.0f})".format(
        len(linhas), regiao or config.UF, config.VALOR_MAXIMO))
    if reais:
        media = sum(reais) / len(reais)
        mediana = sorted(reais)[len(reais) // 2]
        print("Preço médio estimado: R$ {:,.2f}  |  mediana: R$ {:,.2f}  "
              "(sobre {} editais com valor informado)".format(media, mediana, len(reais)))
    if n_simbolicos:
        print("({} editais com valor simbólico/sigiloso ficaram fora da média)".format(n_simbolicos))
    print("=" * 78)
    print("{:<18} {:<52} {:>11}  {}".format("LOCAL", "O QUE ESTÃO COMPRANDO", "VALOR", "ENCERRA"))
    print("-" * 90)
    for l in linhas[:top]:
        local = "{}/{}".format(l["municipio"], l["uf"])[:18]
        objeto = " ".join((l["objeto"] or "").split())[:52]
        if l["valor_estimado"] and l["valor_estimado"] >= config.VALOR_PISO_CONFIAVEL:
            valor = "R$ {:,.0f}".format(l["valor_estimado"])
        else:
            valor = "(sigiloso)"
        print("{:<18} {:<52} {:>11}  {}".format(
            local, objeto, valor, _dia_mes(l["encerramento"])))
    if len(linhas) > top:
        print("... +{} editais no CSV ({}).".format(len(linhas) - top, config.CSV_RADAR))


def imprimir_ranking(linhas, top=15):
    """Mostra os primeiros editais ranqueados de forma legível."""
    print("\n" + "=" * 70)
    print("TOP {} EDITAIS MAIS FAVORÁVEIS (estimativa, não garantia)".format(min(top, len(linhas))))
    print("=" * 70)
    for i, l in enumerate(linhas[:top], 1):
        print("\n#{} [score {}] {} — {}/{}".format(
            i, l["score"], l["orgao"], l["municipio"], l["uf"]))
        print("   Objeto: {}".format((l["objeto"] or "")[:120]))
        print("   Valor estimado: R$ {:,.2f} | {} | encerra {} ({} dias)".format(
            l["valor_estimado"], l["modalidade"], l["encerramento"], l["dias_para_encerrar"]))
        print("   Sinais: {}".format(l["sinais"]))
        print("   Link: {}".format(l["link_edital"]))


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main(argv):
    debug = "--debug" in argv
    top = 15
    if "--top" in argv:
        try:
            top = int(argv[argv.index("--top") + 1])
        except (ValueError, IndexError):
            pass

    # Passo 0 — conectividade
    ok, msg = api.testar_conectividade()
    print(msg)
    if not ok:
        sys.exit(2)

    print("\nLEMBRETE: os scores são ESTIMATIVAS de favorabilidade — onde há menos")
    print("disputa e mais margem para um fornecedor pequeno. NÃO são probabilidade")
    print("de vitória. Exigências de habilitação moram no PDF do edital.\n")

    so_fechada = config.SO_PROPOSTA_FECHADA or "--fechado" in argv
    if so_fechada:
        print("Filtro: SÓ proposta fechada / sem lance ao vivo (você envia um valor antes).\n")

    # --brasil busca em todo o país (faz sentido com proposta fechada: sem
    # comparecimento, a localização só afeta o frete). Senão, usa a sua UF.
    uf = None if "--brasil" in argv else config.UF
    if uf is None:
        print("Abrangência: BRASIL inteiro (localização só pesa no frete).\n")

    editais = coletar_editais_abertos(debug=debug, uf=uf)
    linhas = filtrar_e_pontuar(editais, so_fechada=so_fechada)

    if not linhas:
        print("\nNenhum edital casou com os filtros. Ajuste config.py "
              "(PALAVRAS_CHAVE, VALOR_MAXIMO, JANELA_DIAS) ou tire --fechado.")
        return

    print("\n{} editais passaram nos filtros (objeto + teto).".format(len(linhas)))
    if "--resumo" in argv:
        imprimir_resumo(linhas, top=top if "--top" in argv else 30, regiao=uf or "BRASIL")
    else:
        imprimir_ranking(linhas, top=top)
    salvar_csv(linhas, config.CSV_RADAR)


if __name__ == "__main__":
    main(sys.argv[1:])
