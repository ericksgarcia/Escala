# -*- coding: utf-8 -*-
"""
Cliente mínimo para a API PÚBLICA de consulta do PNCP.

Usa apenas a biblioteca padrão (urllib, json) — zero dependências externas,
para não esbarrar em problemas de pip/rede no sandbox.

A API de consulta NÃO exige login. Só as APIs de manutenção (inserir/editar)
pedem credencial — e essas não são usadas aqui.

Princípios:
- Pagina corretamente usando "totalPaginas".
- Trata erros de rede/HTTP com retry e backoff exponencial.
- Nunca quebra por um campo ausente: use `pegar()` para acessar campos aninhados.
- Permite introspecção do JSON real antes de confiar em nomes de campo.
"""

import json
import time
import urllib.parse
import urllib.request
import urllib.error

import config


class ErroRede(Exception):
    """Falha de rede/HTTP depois de esgotar as tentativas."""


def _montar_url(endpoint, params):
    """Monta a URL completa a partir do endpoint e dos parâmetros de query."""
    # Remove parâmetros None/"" para não poluir a query.
    limpos = {k: v for k, v in (params or {}).items() if v not in (None, "")}
    query = urllib.parse.urlencode(limpos)
    base = config.BASE_URL.rstrip("/")
    url = "{}/{}".format(base, endpoint.lstrip("/"))
    if query:
        url = "{}?{}".format(url, query)
    return url


def _buscar_url(url):
    """
    Núcleo de requisição GET (JSON) com retry e backoff exponencial.

    Devolve o JSON decodificado. Levanta ErroRede após esgotar as tentativas e
    ValueError para respostas 4xx / não-JSON (o chamador decide se pula).
    """
    ultima_excecao = None
    for tentativa in range(config.MAX_TENTATIVAS):
        try:
            req = urllib.request.Request(
                url, headers={"Accept": "application/json", "User-Agent": "garimpo-pncp/1.0"}
            )
            with urllib.request.urlopen(req, timeout=config.TIMEOUT) as resp:
                # 204 = sem registros para os filtros dados.
                if resp.status == 204:
                    return {"data": [], "totalPaginas": 0, "totalRegistros": 0}
                bruto = resp.read().decode("utf-8")
                if not bruto.strip():
                    return {"data": [], "totalPaginas": 0, "totalRegistros": 0}
                try:
                    return json.loads(bruto)
                except json.JSONDecodeError:
                    # Resposta não-JSON (ex.: modalidade inexistente devolve HTML).
                    raise ValueError("Resposta não-JSON em {}".format(url))

        except urllib.error.HTTPError as e:
            # 4xx normalmente não adianta repetir (parâmetro inválido).
            if 400 <= e.code < 500 and e.code not in (429,):
                raise ValueError("HTTP {} em {}".format(e.code, url))
            ultima_excecao = e
        except (urllib.error.URLError, TimeoutError, ConnectionError) as e:
            ultima_excecao = e

        # Backoff exponencial: 2s, 4s, 8s, 16s
        if tentativa < config.MAX_TENTATIVAS - 1:
            time.sleep(2 ** (tentativa + 1))

    raise ErroRede("Falha ao acessar {} após {} tentativas: {}".format(
        url, config.MAX_TENTATIVAS, ultima_excecao))


def requisitar(endpoint, params=None):
    """
    Faz UMA requisição GET à API de CONSULTA e devolve o JSON decodificado.

    Levanta ErroRede após esgotar as tentativas; ValueError para 4xx/não-JSON
    (ex.: códigos de modalidade inválidos devolvem HTML — o chamador pula).
    """
    return _buscar_url(_montar_url(endpoint, params))


def buscar_itens_edital(numero_controle):
    """
    Busca os ITENS de um edital (preço unitário, quantidade, unidade, descrição).

    Os itens NÃO estão na API de consulta; ficam na API pncp:
      /api/pncp/v1/orgaos/{cnpj}/compras/{ano}/{sequencial}/itens
    O identificador vem do numeroControlePNCP ('{cnpj}-{tipo}-{seq}/{ano}').
    Validado em runtime: devolve lista com valorUnitarioEstimado, quantidade,
    unidadeMedida, valorTotal, descricao, orcamentoSigiloso, tipoBeneficioNome.

    Devolve [] em qualquer erro (nunca quebra o fluxo).
    """
    if not numero_controle:
        return []
    try:
        esquerda, ano = numero_controle.split("/")
        cnpj, _tipo, sequencial = esquerda.split("-")
        seq = int(sequencial)
    except (ValueError, TypeError):
        return []
    url = "{}/v1/orgaos/{}/compras/{}/{}/itens".format(
        config.BASE_PNCP.rstrip("/"), cnpj, ano, seq)
    try:
        dados = _buscar_url(url)
    except (ErroRede, ValueError):
        return []
    # O endpoint devolve uma lista direta; tolera envelope {"data": [...]}.
    if isinstance(dados, dict):
        dados = dados.get("data") or []
    return dados if isinstance(dados, list) else []


def paginar(endpoint, params=None, max_paginas=None, verbose=False):
    """
    Gera (yield) cada item de TODAS as páginas de um endpoint paginado do PNCP.

    O PNCP usa "pagina" (1-based) e devolve "totalPaginas". Paramos quando
    chegamos ao total, quando uma página volta vazia, ou ao atingir max_paginas.

    Itens com resposta inválida (ValueError) interrompem a paginação daquele
    endpoint de forma silenciosa — útil para varrer faixas de modalidade.
    """
    params = dict(params or {})
    pagina = 1
    total_paginas = None

    while True:
        params["pagina"] = pagina
        try:
            envelope = requisitar(endpoint, params)
        except ValueError:
            # Parâmetro/endpoint inválido para esta combinação: encerra.
            return

        dados = envelope.get("data") or []
        if total_paginas is None:
            total_paginas = envelope.get("totalPaginas") or 0
            if verbose:
                print("    [{}] {} registros em {} páginas".format(
                    params.get("codigoModalidadeContratacao", "-"),
                    envelope.get("totalRegistros"), total_paginas))

        if not dados:
            return

        for item in dados:
            yield item

        if pagina >= total_paginas:
            return
        if max_paginas is not None and pagina >= max_paginas:
            return
        pagina += 1


def buscar_resultados_item(numero_controle, num_item):
    """
    Busca os RESULTADOS de um item (quem venceu e por quanto).

    Endpoint pncp:
      /api/pncp/v1/orgaos/{cnpj}/compras/{ano}/{seq}/itens/{num}/resultados
    Campos úteis: valorUnitarioHomologado, valorTotalHomologado,
    quantidadeHomologada, nomeRazaoSocialFornecedor, niFornecedor,
    porteFornecedorNome. Devolve [] em qualquer erro.

    OBS: o campo 'percentualDesconto' da API é inconfiável — calcule o desconto
    a partir de (estimado - homologado) / estimado.
    """
    if not numero_controle:
        return []
    try:
        esquerda, ano = numero_controle.split("/")
        cnpj, _tipo, sequencial = esquerda.split("-")
        seq = int(sequencial)
    except (ValueError, TypeError):
        return []
    url = "{}/v1/orgaos/{}/compras/{}/{}/itens/{}/resultados".format(
        config.BASE_PNCP.rstrip("/"), cnpj, ano, seq, num_item)
    try:
        dados = _buscar_url(url)
    except (ErroRede, ValueError):
        return []
    if isinstance(dados, dict):
        dados = dados.get("data") or []
    return dados if isinstance(dados, list) else []


def corrigir_texto(s):
    """
    Corrige "mojibake" (texto UTF-8 que foi gravado como latin-1) presente em
    parte dos dados do PNCP — ex.: 'ÃCIDO ÃRICO' -> 'ÁCIDO ÚRICO'.

    Aplica a reversão só quando ela produz UTF-8 válido; caso contrário devolve
    o texto original (strings já corretas não são alteradas).
    """
    if not s:
        return s
    try:
        return s.encode("latin-1").decode("utf-8")
    except (UnicodeEncodeError, UnicodeDecodeError):
        return s


def pegar(dicionario, caminho, padrao=None):
    """
    Acesso seguro a campos aninhados via caminho pontilhado.

    Ex.: pegar(item, "orgaoEntidade.razaoSocial") nunca levanta KeyError;
    devolve `padrao` se qualquer nível faltar. Essencial porque a cobertura
    do PNCP é irregular e campos faltam com frequência.
    """
    atual = dicionario
    for parte in caminho.split("."):
        if isinstance(atual, dict) and parte in atual:
            atual = atual[parte]
        else:
            return padrao
    return atual if atual is not None else padrao


def introspeccionar(item, titulo="PRIMEIRO ITEM (formato real)"):
    """
    Imprime o JSON real de um item para conferência dos nomes de campo.

    Conforme o aviso da tarefa: NÃO confie cegamente nos nomes; confirme em
    runtime. Chame isto na primeira execução / em modo --debug.
    """
    print("=" * 70)
    print(titulo)
    print("=" * 70)
    print(json.dumps(item, indent=2, ensure_ascii=False))
    print("=" * 70)


def testar_conectividade():
    """
    Passo 0: confirma que o sandbox alcança pncp.gov.br.

    Devolve (ok: bool, mensagem: str). NÃO tenta contornar bloqueio de rede —
    apenas reporta para o usuário liberar o domínio na configuração da tarefa.
    """
    from datetime import date, timedelta
    data_final = (date.today() + timedelta(days=7)).strftime("%Y%m%d")
    try:
        env = requisitar("/v1/contratacoes/proposta", {
            "dataFinal": data_final,
            "codigoModalidadeContratacao": 6,
            "pagina": 1,
        })
        total = env.get("totalRegistros")
        return True, "Conexão OK com PNCP. Pregões eletrônicos abertos (amostra): {}".format(total)
    except ErroRede as e:
        return False, (
            "SEM ACESSO a pncp.gov.br. Libere o domínio na configuração de rede "
            "da tarefa e rode de novo. Detalhe: {}".format(e))
