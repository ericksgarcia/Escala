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
VALOR_MAXIMO = 10000.0

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
TIMEOUT = 40           # segundos por requisição
MAX_TENTATIVAS = 4     # retries com backoff exponencial (2s, 4s, 8s, 16s)

# Arquivos de saída
CSV_RADAR = "saida_radar.csv"
CSV_VIABILIDADE = "saida_viabilidade.csv"
