# -*- coding: utf-8 -*-
"""
Configuração central do garimpo de editais no PNCP.

Tudo que é "perfil do fornecedor" e parâmetros de busca mora aqui.
Edite este arquivo (ou exporte variáveis de ambiente equivalentes) antes de rodar.

AVISO HONESTO: nada aqui prevê vitória. Os scores são heurísticas transparentes
que apenas indicam ONDE um fornecedor pequeno tende a ter MENOS disputa e MAIS
margem. A decisão final depende do edital (PDF), das exigências de habilitação e
da sua execução comercial.
"""

# ---------------------------------------------------------------------------
# [MEUS DADOS] — preencha conforme o seu negócio
# ---------------------------------------------------------------------------

# O que eu vendo / forneço — palavras-chave que aparecem no campo "objetoCompra".
# Como o usuário vende "produtos físicos variados", começamos com termos amplos
# típicos de compras de bens. AJUSTE para os seus produtos reais (ex.: "papel",
# "cadeira", "epi", "ferramenta"). Quanto mais específico, melhor o ranking.
# A busca é case-insensitive e ignora acentos.
PALAVRAS_CHAVE = [
    "aquisição",
    "aquisicao",
    "material",
    "materiais",
    "fornecimento",
    "equipamento",
    "kit",
    "produto",
    "suprimento",
    "mobiliário",
    "ferramenta",
    "utensílio",
]

# Estado (UF) onde eu consigo / prefiro atuar. Usado como filtro na API.
UF = "MG"

# Valor máximo de contrato que consigo executar (R$). Editais acima disso são
# descartados no radar (ou pontuados negativamente, conforme configuração).
VALOR_MAXIMO = 50000.0

# Prazo mínimo (em dias) que preciso para preparar uma proposta. Editais que
# encerram antes disso perdem pontos (ou são descartados, ver DESCARTAR_*).
PRAZO_MINIMO_DIAS = 10

# Piso de valor confiável (R$). Muitos órgãos publicam valor estimado simbólico
# (R$ 0,01 / R$ 1,00) quando o orçamento é sigiloso ou ainda não definido.
# Abaixo deste piso, NÃO tratamos o valor como "baixo/favorável" — marcamos como
# "valor não informado" para não inflar o ranking com editais cujo valor real
# desconhecemos. Observado no dado real (2026-06).
VALOR_PISO_CONFIAVEL = 100.0

# ---------------------------------------------------------------------------
# Parâmetros de busca do radar
# ---------------------------------------------------------------------------

# Janela de dias à frente para procurar editais com proposta em aberto.
# A API exige uma "dataFinal" (yyyymmdd); usamos hoje + JANELA_DIAS.
JANELA_DIAS = 30

# Códigos de modalidade a varrer no endpoint de proposta aberta.
# Validados em runtime (2026-06): 1 Leilão-E, 3 Concurso, 4 Concorrência-E,
# 5 Concorrência-P, 6 Pregão-E, 7 Pregão-P, 8 Dispensa, 9 Inexigibilidade,
# 10 Manif. Interesse, 12 Credenciamento, 13 Leilão-P.
# Os códigos 2, 11 e 14 retornam erro/HTML e são pulados automaticamente.
# Para fornecedor pequeno de bens, o que mais importa é Pregão-E (6) e Dispensa (8).
MODALIDADES = [6, 8, 4, 12, 1, 13, 7, 5, 3, 9, 10]

# Modalidades consideradas "ágeis" (menos burocracia, ciclo curto) -> ganham ponto.
MODALIDADES_AGEIS = {6, 8}  # Pregão Eletrônico, Dispensa

# Modos de disputa SEM lances ao vivo — você envia UMA proposta antes e pronto:
#   2 = Fechado (proposta lacrada, abre tudo junto, menor preço ganha)
#   5 = Não se aplica (credenciamento/sem disputa de preço)
# Os modos 1 (Aberto), 3 (Aberto-Fechado) e 4 (Dispensa com disputa) têm lance ao vivo.
MODOS_DISPUTA_SEM_LANCE = {2, 5}

# Se True (ou --fechado na linha de comando), o radar mostra SÓ editais de
# proposta fechada/sem lance ao vivo.
SO_PROPOSTA_FECHADA = False

# Se True, descarta de vez editais acima do teto de valor. Se False, mantém no
# CSV mas com pontuação reduzida (útil para enxergar o mercado todo).
DESCARTAR_ACIMA_DO_TETO = True

# Se True, descarta editais cujo prazo até o encerramento é menor que
# PRAZO_MINIMO_DIAS. Se False, mantém com pontuação reduzida.
DESCARTAR_PRAZO_CURTO = False

# Limite de páginas por modalidade (proteção contra varreduras enormes).
# Cada página traz ~10 itens. None = sem limite (puxa tudo).
MAX_PAGINAS_POR_MODALIDADE = 50

# ---------------------------------------------------------------------------
# Parâmetros do estimador de viabilidade (Camada 2)
# ---------------------------------------------------------------------------

# Quantos meses de histórico de contratos puxar para o mesmo órgão.
VIABILIDADE_MESES_HISTORICO = 12

# Desconto típico do vencedor sobre o valor estimado, usado como palpite quando
# não há histórico suficiente para calcular. É um chute conservador, NÃO um dado.
DESCONTO_TIPICO_PADRAO = 0.15  # 15%

# Limite de páginas de contratos por órgão (proteção).
VIABILIDADE_MAX_PAGINAS = 100

# ---------------------------------------------------------------------------
# Margem líquida com frete (margem.py)
# ---------------------------------------------------------------------------

# Sua base de operação (de onde saem as entregas).
BASE_CIDADE = "Belo Horizonte"
BASE_UF = "MG"

# Imposto sobre a venda (%). Ajuste ao seu regime (Simples Nacional costuma
# ficar entre 6% e 15% dependendo do anexo/faturamento).
IMPOSTO_PCT = 0.10

# Desconto típico do vencedor sobre o valor estimado (mediana do histórico ~21%).
# Usado como "preço que você provavelmente precisaria praticar para ganhar".
DESCONTO_DISPUTA_PCT = 0.21

# MODO TRIAGEM: quando você NÃO informa o custo real do item, assumimos que o
# seu custo de compra é esta fração do valor estimado do edital. Ajuste ao seu
# poder de compra (0.55 = você compra a ~55% do preço de referência).
CUSTO_PCT_DO_ESTIMADO = 0.55

# Frete por entrega (R$). Piso típico de transportadora fracionada saindo de BH
# para o interior. A parcelada (SRP) multiplica isto pelo nº de entregas.
FRETE_POR_ENTREGA = 120.0

# Nº de entregas presumido em registro de preços (parcelada). Entrega única = 1.
ENTREGAS_SRP = 6

# Teto de "frete como % do valor": acima disso o edital é marcado como inviável
# por logística (frete come a margem).
FRETE_PCT_MAXIMO = 0.15

# Arquivo opcional com custos reais (MODO PRECISO). Formato CSV:
#   trecho_descricao,custo_unitario
# Ex.:  manta microfibra,30.00
# O primeiro trecho que casar (sem acento, minúsculo) com a descrição é usado.
ARQUIVO_CUSTOS = "custos.csv"

# ---------------------------------------------------------------------------
# Histórico "edital pediu X / vencedor foi Y" (historico.py)
# ---------------------------------------------------------------------------

# Quantos resultados (itens já homologados) coletar para o histórico.
HISTORICO_ALVO = 30

# Janela do passado a varrer (dias atrás). Editais publicados há mais tempo têm
# maior chance de já estarem homologados (com resultado/vencedor).
HISTORICO_DIA_INICIO = 365   # começa a olhar a partir de X dias atrás
HISTORICO_DIA_FIM = 45       # até X dias atrás (recentes demais ainda não têm resultado)

# Se True, filtra o histórico pelas suas PALAVRAS_CHAVE (seu nicho). Se False,
# pega qualquer objeto. Pode sobrescrever com --todas na linha de comando.
HISTORICO_SO_MEU_NICHO = True

# ---------------------------------------------------------------------------
# CEIS/CNEP (opcional) — empresas impedidas/punidas
# ---------------------------------------------------------------------------
# A consulta CEIS/CNEP via Portal da Transparência exige uma chave de API
# (cabeçalho "chave-api-dados"). Sem chave, a checagem é pulada com aviso.
# Coloque a chave aqui ou na variável de ambiente PORTAL_TRANSPARENCIA_API_KEY.
PORTAL_TRANSPARENCIA_API_KEY = ""

# ---------------------------------------------------------------------------
# Infra / rede
# ---------------------------------------------------------------------------

BASE_URL = "https://pncp.gov.br/api/consulta"
# Base da API "pncp" (itens do edital — preço unitário e quantidade ficam aqui,
# não na API de consulta).
BASE_PNCP = "https://pncp.gov.br/api/pncp"
TIMEOUT = 40           # segundos por requisição
MAX_TENTATIVAS = 4     # retries com backoff exponencial (2s, 4s, 8s, 16s)

# Arquivos de saída
CSV_RADAR = "saida_radar.csv"
CSV_VIABILIDADE = "saida_viabilidade.csv"
CSV_ITENS = "saida_itens.csv"
