# -*- coding: utf-8 -*-
"""
Histórico "o edital pediu X / o vencedor foi Y".

Para licitações JÁ HOMOLOGADAS (com resultado) em MG, cruza:
  - valorUnitarioEstimado  (o que o edital pedia, preço de referência)  ->
  - valorUnitarioHomologado (por quanto o vencedor fechou)
e mostra o desconto, o vencedor e o porte (ME/EPP/grande).

Serve para você CALIBRAR sua proposta: ver quanto, na prática, o vencedor
costuma descontar sobre o valor de referência em compras parecidas.

LIMITAÇÕES HONESTAS:
  - Só aparecem itens já homologados (recentes demais ainda não têm resultado).
  - Quando o orçamento foi sigiloso, não há estimado para comparar (pulado).
  - É amostra do que está publicado no PNCP; cobertura é incompleta.
  - Isto é histórico/estatística, NÃO garantia de que o próximo será igual.

Uso:
    python3 historico.py            # ~30 resultados do seu nicho (PALAVRAS_CHAVE)
    python3 historico.py --todas    # qualquer objeto, não só o seu nicho
    python3 historico.py --n 50     # alvo de 50 resultados
"""

import csv
import sys
import unicodedata
from datetime import date, timedelta

import config
import pncp_api as api


def _link_edital(nc):
    """numeroControlePNCP 'cnpj-tipo-seq/ano' -> URL pública do edital."""
    try:
        esq, ano = nc.split("/")
        cnpj, _t, seq = esq.split("-")
        return "https://pncp.gov.br/app/editais/{}/{}/{}".format(cnpj, ano, int(seq))
    except (ValueError, AttributeError):
        return ""


def _normalizar(texto):
    if not texto:
        return ""
    s = unicodedata.normalize("NFKD", texto)
    return "".join(c for c in s if not unicodedata.combining(c)).lower()


_KW = [_normalizar(k) for k in config.PALAVRAS_CHAVE]


def _casa_nicho(objeto):
    obj = _normalizar(objeto)
    return any(k and k in obj for k in _KW)


# Pistas de entrega parcelada (registro de preços) — para o filtro de entrega única.
_PISTAS_SRP = [_normalizar(x) for x in (
    "registro de preco", "registro de precos", "eventual", "parcelada",
    "sob demanda", "fornecimento continuo", "futura e eventual", "futuro e eventual")]


def eh_srp(objeto):
    o = _normalizar(objeto)
    return any(p in o for p in _PISTAS_SRP)


def _melhor_resultado(resultados):
    """Escolhe o resultado vencedor (1ª classificação SRP, senão o primeiro)."""
    if not resultados:
        return None
    vencedores = [r for r in resultados if api.pegar(r, "ordemClassificacaoSrp") == 1]
    return (vencedores or resultados)[0]


def coletar(alvo, so_nicho, so_unica=False):
    """
    Varre contratações publicadas no passado (janela configurável), em MG, nas
    modalidades ágeis, e coleta itens homologados (estimado vs vencedor).

    so_unica=True descarta entregas parceladas (registro de preços), mantendo
    apenas compras de entrega única.
    """
    registros = []
    hoje = date.today()
    # Janelas de 30 dias, do mais antigo para o mais novo dentro do intervalo.
    inicio = hoje - timedelta(days=config.HISTORICO_DIA_INICIO)
    fim = hoje - timedelta(days=config.HISTORICO_DIA_FIM)

    print("Buscando licitações homologadas em {} de {} a {} ...".format(
        config.UF, inicio.isoformat(), fim.isoformat()))
    if so_nicho:
        print("Filtro: só o seu nicho ({} palavras-chave). Use --todas para abrir.".format(len(_KW)))
    if so_unica:
        print("Filtro: só ENTREGA ÚNICA (pula registro de preços/parcelada).")

    janela_ini = inicio
    while janela_ini < fim and len(registros) < alvo:
        janela_fim = min(janela_ini + timedelta(days=30), fim)
        for modalidade in sorted(config.MODALIDADES_AGEIS):
            if len(registros) >= alvo:
                break
            params = {
                "dataInicial": janela_ini.strftime("%Y%m%d"),
                "dataFinal": janela_fim.strftime("%Y%m%d"),
                "codigoModalidadeContratacao": modalidade,
                "uf": config.UF,
            }
            for compra in api.paginar("/v1/contratacoes/publicacao", params, max_paginas=30):
                if len(registros) >= alvo:
                    break
                objeto = api.corrigir_texto(api.pegar(compra, "objetoCompra", ""))
                if so_nicho and not _casa_nicho(objeto):
                    continue
                if so_unica and eh_srp(objeto):
                    continue
                nc = api.pegar(compra, "numeroControlePNCP", "")
                itens = api.buscar_itens_edital(nc)
                # No máx. 2 itens homologados por compra (diversidade).
                usados = 0
                for it in itens:
                    if usados >= 2 or len(registros) >= alvo:
                        break
                    if not api.pegar(it, "temResultado"):
                        continue
                    est = api.pegar(it, "valorUnitarioEstimado")
                    if not isinstance(est, (int, float)) or est <= 0:
                        continue  # sigiloso/sem referência: não dá pra comparar
                    res = _melhor_resultado(
                        api.buscar_resultados_item(nc, api.pegar(it, "numeroItem")))
                    if not res:
                        continue
                    hom = api.pegar(res, "valorUnitarioHomologado")
                    if not isinstance(hom, (int, float)) or hom <= 0:
                        continue
                    desconto = (est - hom) / est * 100.0
                    registros.append({
                        "data": api.pegar(res, "dataResultado", ""),
                        "orgao": api.pegar(compra, "orgaoEntidade.razaoSocial", ""),
                        "municipio": api.pegar(compra, "unidadeOrgao.municipioNome", ""),
                        "uf": api.pegar(compra, "unidadeOrgao.ufSigla", ""),
                        "item": api.corrigir_texto(api.pegar(it, "descricao", "")),
                        "quantidade": api.pegar(it, "quantidade", ""),
                        "unidade": api.pegar(it, "unidadeMedida", ""),
                        "estimado_unit": est,
                        "vencedor_unit": hom,
                        "desconto_pct": round(desconto, 1),
                        "vencedor": api.pegar(res, "nomeRazaoSocialFornecedor", ""),
                        "porte": api.pegar(res, "porteFornecedorNome", ""),
                        "link": _link_edital(nc),
                    })
                    usados += 1
                if len(registros) >= alvo:
                    break
            print("  janela {}..{} mod {}: {} resultados acumulados".format(
                janela_ini.strftime("%d/%m"), janela_fim.strftime("%d/%m"),
                modalidade, len(registros)))
        janela_ini = janela_fim

    return registros


def _trim(s, n=46):
    s = " ".join((s or "").split())
    h = len(s) // 2
    if h > 8 and s[:h].strip() == s[h:].strip():
        s = s[:h].strip()
    return s if len(s) <= n else s[:n].rstrip() + "…"


def imprimir(registros):
    print("\n" + "=" * 96)
    print("HISTÓRICO: o edital pedia (estimado) × o vencedor fechou (homologado)")
    print("=" * 96)
    print("{:<8} {:<20} {:<34} {:>10} {:>10} {:>7}".format(
        "DATA", "LOCAL", "ITEM", "ESTIM.", "VENC.", "DESC."))
    print("-" * 96)
    descontos = []
    for r in registros:
        descontos.append(r["desconto_pct"])
        print("{:<8} {:<20} {:<34} {:>10} {:>10} {:>6}%".format(
            (r["data"] or "")[-5:] or r["data"],
            "{}/{}".format(r["municipio"], r["uf"])[:20],
            _trim(r["item"], 34),
            "R${:,.2f}".format(r["estimado_unit"])[:10],
            "R${:,.2f}".format(r["vencedor_unit"])[:10],
            r["desconto_pct"]))
    if descontos:
        descontos.sort()
        media = sum(descontos) / len(descontos)
        mediana = descontos[len(descontos) // 2]
        print("-" * 96)
        print("Desconto do vencedor sobre o estimado — média {:.1f}% | mediana {:.1f}% "
              "(em {} itens)".format(media, mediana, len(descontos)))
        zerados = sum(1 for d in descontos if d <= 0.5)
        print("{} de {} itens fecharam praticamente no valor estimado (desconto ~0%).".format(
            zerados, len(descontos)))


def salvar_csv(registros, caminho):
    if not registros:
        return
    campos = ["data", "orgao", "municipio", "uf", "item", "quantidade", "unidade",
              "estimado_unit", "vencedor_unit", "desconto_pct", "vencedor", "porte", "link"]
    with open(caminho, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=campos)
        w.writeheader()
        w.writerows(registros)
    print("CSV salvo em: {}".format(caminho))


def main(argv):
    alvo = config.HISTORICO_ALVO
    if "--n" in argv:
        try:
            alvo = int(argv[argv.index("--n") + 1])
        except (ValueError, IndexError):
            pass
    so_nicho = config.HISTORICO_SO_MEU_NICHO and "--todas" not in argv
    so_unica = "--unica" in argv

    ok, msg = api.testar_conectividade()
    print(msg)
    if not ok:
        sys.exit(2)

    print("\nLEMBRETE: histórico/estatística, NÃO garantia. Só itens já homologados;")
    print("orçamentos sigilosos ficam de fora (não há estimado para comparar).\n")

    registros = coletar(alvo, so_nicho, so_unica)
    if not registros:
        print("\nNenhum resultado homologado encontrado nessa janela/nicho. "
              "Tente --todas ou ajuste HISTORICO_DIA_* em config.py.")
        return
    imprimir(registros)
    salvar_csv(registros, "saida_historico.csv")


if __name__ == "__main__":
    main(sys.argv[1:])
