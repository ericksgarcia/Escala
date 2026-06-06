# Garimpo de editais favoráveis no PNCP

Ferramenta em **Python puro (só biblioteca padrão)** que encontra licitações
públicas **abertas** no [PNCP](https://pncp.gov.br) (Portal Nacional de
Contratações Públicas) em que um **fornecedor pequeno tem boa chance** — e cruza
o histórico de contratos para estimar concorrência e preço-alvo.

> ⚠️ **Isto é uma ESTIMATIVA, não uma garantia de vitória.** Os scores apontam
> *onde tende a haver menos disputa e mais margem* para um fornecedor pequeno.
> Eles **não** são "probabilidade de ganhar". A decisão de quem vence depende do
> edital (PDF), das exigências de habilitação e da sua execução comercial.

## O que é

Duas camadas independentes:

1. **`radar.py` — Radar de oportunidades.** Puxa as contratações com *proposta em
   aberto*, filtra por UF, palavras-chave do objeto e teto de valor, e **ranqueia
   por favorabilidade** com uma heurística transparente. Salva `saida_radar.csv`.

2. **`viabilidade.py` — Estimador de viabilidade.** Para os melhores editais do
   radar, cruza o histórico de `/v1/contratos` do **mesmo órgão** e estima
   concorrência (proxy), vencedores recorrentes, **preço-alvo** e margem. Produz um
   **score de viabilidade com explicação textual** fator a fator. Salva
   `saida_viabilidade.csv`.

## Configuração de rede (importante)

A ferramenta acessa a **API pública de consulta** do PNCP
(`https://pncp.gov.br/api/consulta`). Essa API **não exige login** — só as APIs de
manutenção (inserir/editar) pedem credencial, e essas **não** são usadas aqui.

Se você roda em um sandbox com rede restrita, **libere o domínio `pncp.gov.br`** na
configuração de rede da tarefa. O `radar.py` faz uma checagem de conectividade
(Passo 0) antes de tudo; se a rede estiver bloqueada, ele **para e avisa** em vez
de tentar contornar.

Para a checagem opcional de CEIS/CNEP (empresas impedidas), também é preciso liberar
`api.portaldatransparencia.gov.br` e configurar uma chave de API (veja abaixo).

## Como configurar

Edite **`config.py`** — bloco `[MEUS DADOS]`:

| Parâmetro | Significado | Valor atual |
|---|---|---|
| `PALAVRAS_CHAVE` | termos que aparecem no `objetoCompra` | termos amplos de bens — **refine para os seus produtos** |
| `UF` | seu estado | `MG` |
| `VALOR_MAXIMO` | maior contrato que você executa (R$) | `10000` |
| `PRAZO_MINIMO_DIAS` | dias que você precisa para montar a proposta | `10` |
| `JANELA_DIAS` | quão à frente procurar editais abertos | `30` |

Outros ajustes úteis: `MODALIDADES`, `DESCARTAR_ACIMA_DO_TETO`,
`DESCARTAR_PRAZO_CURTO`, `VIABILIDADE_MESES_HISTORICO`, `DESCONTO_TIPICO_PADRAO`.

> A `PALAVRAS_CHAVE` começa com termos genéricos de bens ("aquisição", "material",
> "equipamento"…) porque o perfil informado foi "produtos físicos variados".
> **Quanto mais específico você for (ex.: "papel", "cadeira", "EPI"), melhor o
> ranking.**

## Como rodar

```bash
cd pncp_garimpo

# 1) Radar — lista e ranqueia editais abertos
python3 radar.py                 # roda e salva saida_radar.csv
python3 radar.py --resumo        # tabela enxuta: o que compram + valor + preço médio
python3 radar.py --top 30        # mostra 30 no terminal
python3 radar.py --debug         # imprime o JSON real do 1º item (introspecção)

# 2) Viabilidade — analisa os melhores do radar
python3 viabilidade.py           # usa saida_radar.csv (top 5)
python3 viabilidade.py --top 8   # analisa os 8 melhores
python3 viabilidade.py --debug   # imprime o JSON real de um contrato
```

Sem dependências externas: **só Python 3 + biblioteca padrão** (`urllib`, `json`,
`csv`). Nada de `pip`.

## Como o score do radar é calculado (transparente)

Cada edital ganha/perde pontos, e **cada ponto vira um "sinal" textual** no CSV:

- **Valor baixo** → cabe no seu teto (+3); provável **exclusivo ME/EPP** se ≤ R$ 80k
  (LC 123/2006, art. 48, I → menos disputa) (+2); acima do teto (−1).
- **Modalidade ágil** (Pregão Eletrônico, Dispensa) → ciclo curto (+2); Dispensa
  costuma ter disputa menor (+1).
- **Prazo** suficiente para preparar (≥ `PRAZO_MINIMO_DIAS`) (+2), folgado (+1);
  curto demais (−2).
- **Registro de preço (SRP)** → fornecimento sob demanda (+1).
- **Proximidade** (mesma UF) (+1).

## Como o score de viabilidade é calculado

A partir do histórico de contratos do **mesmo órgão**, filtrado pelas palavras-chave:

- **Margem** — o preço-alvo cabe no seu teto? (até 30 pts)
- **Pulverização do mercado** — mercado pulverizado (líder com fatia pequena, muitos
  fornecedores) abre brecha; concentrado indica incumbente forte (até 40 pts).
- **Lastro** — quantos contratos similares dão confiança à estimativa (até 20 pts).
- **Incumbente impedido** no CEIS/CNEP (opcional) — pode abrir espaço (até 10 pts).

O **preço-alvo** é o **menor** entre (a) a mediana dos valores vencedores similares no
órgão (dado real) e (b) o valor estimado do edital menos um desconto típico
(`DESCONTO_TIPICO_PADRAO`, um palpite conservador).

## CEIS/CNEP (opcional)

Para checar se algum incumbente está impedido, configure uma chave do
[Portal da Transparência](https://api.portaldatransparencia.gov.br/) em
`config.PORTAL_TRANSPARENCIA_API_KEY` ou na variável de ambiente
`PORTAL_TRANSPARENCIA_API_KEY`. Sem chave, a checagem é **pulada com aviso** — nada
quebra.

## Limitações conhecidas (leia com atenção)

- **É estimativa, não garantia.** O score não prevê vitória; mede *favorabilidade*.
- **Não vemos os perdedores.** A API de contratos mostra o **vencedor e o valor**,
  mas **não quantos licitantes disputaram**. A "concorrência provável" é um **proxy**
  pela diversidade de fornecedores que já ganharam no órgão.
- **Histórico curto.** A obrigatoriedade plena da Lei 14.133 é recente (~2024), então
  a camada preditiva tem **poucos anos de lastro**. Trate os números como indício.
- **Habilitação mora no PDF.** Exigências que eliminam um fornecedor (atestados,
  certidões, capital mínimo) estão no **PDF do edital**, fora dos campos estruturados.
  Extração de PDF é **melhoria futura**.
- **Cobertura incompleta.** Municípios com menos de 20 mil habitantes têm transição
  até 2027; parte das compras ainda é presencial/fora do portal.
- **Nomes de campo confirmados em runtime.** O parsing foi ajustado ao **JSON real**
  da API (use `--debug` para reinspecionar). Códigos de modalidade são varridos com
  tolerância a erro — códigos inválidos são pulados, não hardcodados cegamente.
  Tabela oficial: <https://www.gov.br/pncp/pt-br/pncp/tabelas-de-dominio>.

## Estrutura

```
pncp_garimpo/
├── config.py        # [MEUS DADOS] + parâmetros de busca
├── pncp_api.py      # cliente HTTP (urllib): paginação, retry/backoff, introspecção
├── radar.py         # Camada 1 — radar de oportunidades
├── viabilidade.py   # Camada 2 — estimador de viabilidade
└── README.md
```
