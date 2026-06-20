# Observabilidade

Este documento explica a stack de observabilidade do backend: o que cada ferramenta
faz, onde o codigo de integracao fica, como configurar do zero e como verificar que
cada peca esta funcionando.

> Nenhum DSN, token ou ID real aparece neste documento. Onde for necessario um valor
> de configuracao, use `.env.example` como referencia e gere as suas proprias
> credenciais nos passos descritos abaixo.

## Visao geral

| Necessidade | Ferramenta | O que resolve |
|---|---|---|
| Erros em produção | **Sentry** | Captura excecoes nao tratadas com stack trace, contexto da requisicao e agrupamento automatico de issues |
| Logs | **structlog** | Logs em JSON estruturado (em vez de texto livre), facil de filtrar/buscar |
| Performance e tracing distribuido | **OpenTelemetry → Grafana Cloud** | Latencia por endpoint, volume de chamadas, rastreio de uma requisicao ponta a ponta |
| Disponibilidade | **`/health`** | Endpoint simples para checagem externa (uptime monitors) |

Todas as ferramentas sao open source (ou rodam sobre software open source com tier
gratuito) e funcionam em modo **push** — ou seja, o proprio processo da API envia os
dados para fora no momento em que algo acontece. Isso é importante porque o backend
roda como **function serverless na Vercel** ([vercel.json](../vercel.json)): nao existe
um processo de longa duracao no ar para ser "raspado" (scrape) por ferramentas como
Prometheus tradicional — por isso essas 3 ferramentas foram escolhidas especificamente
por serem compativeis com esse modelo.

## Sentry (rastreamento de erros)

**O que é:** ferramenta que captura excecoes automaticamente, mostra o stack trace
completo, o contexto da requisicao que falhou, e agrupa erros parecidos na mesma
"issue" para nao gerar ruido repetido.

**Onde fica o codigo:**
- Inicializacao: [app/core/logging.py](../app/core/logging.py) — dentro de
  `setup_logging()`, se `settings.SENTRY_DSN` estiver preenchido, chama
  `sentry_sdk.init(...)`.
- Configuracao: `SENTRY_DSN` em [app/core/config.py](../app/core/config.py).
- Chamado na inicializacao da app em [app/main.py](../app/main.py) (`setup_logging()`).

**Como configurar:**
1. Crie uma conta gratuita em [sentry.io](https://sentry.io).
2. Crie um projeto novo escolhendo a plataforma **Python → FastAPI**.
3. Copie o DSN gerado (formato `https://<chave>@<org>.ingest.<regiao>.sentry.io/<id>`).
4. Localmente: cole em `SENTRY_DSN=` no seu `.env` (nunca commite esse arquivo).
5. Em produção (Vercel): Settings → Environment Variables → adicione `SENTRY_DSN` com
   o mesmo valor, marcando o ambiente "Production".
6. Sem essa variável preenchida, o Sentry simplesmente não é inicializado — nenhuma
   mudança de comportamento, nenhum erro.

**Como verificar que está funcionando:**
1. Rode a API localmente (`uvicorn app.main:app --reload`) com `SENTRY_DSN` preenchido.
2. Force uma excecao (ex.: chame um endpoint passando um parametro invalido que gere
   erro 500, ou adicione temporariamente um `raise Exception("teste sentry")` em
   qualquer rota).
3. No painel do Sentry, abra o projeto do backend → menu **"Issues"** → o erro deve
   aparecer em poucos segundos, com stack trace completo.

**Taxa de amostragem:** `traces_sample_rate=0.1` (10% das requisicoes geram dados de
performance além dos erros, que são sempre 100% capturados).

## Logs estruturados (structlog)

**O que é:** em vez de logs em texto livre (`"Usuario X fez login"`), os logs saem em
JSON (`{"event": "login", "user_id": "X", "level": "info", "timestamp": "..."}`).
Isso facilita filtrar e buscar logs em ferramentas de agregação, e a Vercel já captura
qualquer saída no stdout como log da function automaticamente.

**Onde fica o codigo:** [app/core/logging.py](../app/core/logging.py) — função
`setup_logging()` configura o `structlog` com processors que adicionam nível, timestamp
em ISO 8601 e renderizam tudo como JSON.

**Como ver os logs:**
- Localmente: aparecem direto no terminal onde o `uvicorn` está rodando.
- Em produção: `vercel logs <nome-do-projeto>` (CLI da Vercel) ou pela aba "Logs" no
  dashboard do projeto na Vercel.

**Como adicionar um log novo em qualquer lugar do código:**

```python
import structlog

logger = structlog.get_logger(__name__)

logger.info("evento_criado", evento_id=evento.id, usuario_id=user_id)
```

Os pares chave-valor (`evento_id=...`, `usuario_id=...`) entram automaticamente como
campos estruturados no JSON final — não precisa formatar string manualmente.

## OpenTelemetry + Grafana Cloud (traces e performance)

**O que é:** tracing distribuído. Cada requisição HTTP que chega na API gera um
"trace" — uma linha do tempo de quanto tempo cada parte da requisição levou (ex.:
tempo total da rota, tempo gasto na consulta ao banco). Isso permite ver, endpoint por
endpoint, qual está lento e por quê.

**Onde fica o codigo:** [app/core/telemetry.py](../app/core/telemetry.py) — função
`setup_telemetry(app)`, chamada em [app/main.py](../app/main.py) logo após a criação do
`FastAPI()`. Ela:
1. Só ativa se `settings.OTEL_EXPORTER_OTLP_ENDPOINT` estiver preenchido (senão, não
   faz nada — zero overhead).
2. Exporta as duas variáveis (`OTEL_EXPORTER_OTLP_ENDPOINT`,
   `OTEL_EXPORTER_OTLP_HEADERS`) para `os.environ`, porque o SDK do OpenTelemetry lê
   essas variáveis pelo padrão `os.getenv` internamente.
3. Instrumenta automaticamente todas as rotas do FastAPI via
   `FastAPIInstrumentor.instrument_app(app)`.

**Como configurar:**
1. Crie uma conta gratuita em [grafana.com](https://grafana.com) (Grafana Cloud).
2. No painel, vá em **Connections → Add new connection** e procure por
   **"OpenTelemetry (OTLP)"**.
3. Escolha a opção de infraestrutura **"Serverless / Other"** (o backend roda na
   Vercel, sem container persistente).
4. Gere um novo token de API (scopes de escrita para métricas/logs/traces já vêm
   pré-selecionados).
5. A própria tela do Grafana monta duas linhas de configuração:
   ```
   export OTEL_EXPORTER_OTLP_ENDPOINT="https://otlp-gateway-..."
   export OTEL_EXPORTER_OTLP_HEADERS="Authorization=Basic%20..."
   ```
6. Copie o valor depois do `=` de cada linha (sem aspas) para:
   - Localmente: `.env` (`OTEL_EXPORTER_OTLP_ENDPOINT=...` e
     `OTEL_EXPORTER_OTLP_HEADERS=...`).
   - Produção (Vercel): mesmas duas variáveis em Settings → Environment Variables.

**Como ver os traces:**
1. No Grafana, abra **"Explore"** no menu lateral.
2. Troque o datasource (dropdown no topo) para o que tem "traces" no nome (datasource
   do Tempo, criado junto com a conexão OTLP).
3. Rode uma query de busca filtrando por **Service Name = `backend-eventos`**.
4. A tabela de resultados mostra cada requisição recente, com método+rota
   (`GET /events`, `POST /tags`, etc.) e duração em milissegundos.

## Health check

`GET /health` ([app/routers/meta.py](../app/routers/meta.py)) executa um `SELECT 1` no
banco antes de responder. Retorna:
- `200 {"status": "ok", "database": "ok"}` quando tudo está saudável.
- `503 {"status": "error", "database": "unreachable"}` quando o banco está
  inacessível.

Use essa rota em qualquer serviço de uptime monitoring (ex.: UptimeRobot, Better
Uptime, ou o próprio monitor de saúde da Vercel) para ser avisado quando a API ou o
banco caírem — sem isso, o `/health` antigo sempre retornava `200`, mesmo com o banco
fora do ar.

## Variáveis de ambiente — referência rápida

Veja [.env.example](../.env.example) para a lista completa com placeholders. As
relacionadas a observabilidade:

| Variável | Para quê serve | Onde obter |
|---|---|---|
| `SENTRY_DSN` | Ativa o Sentry (erros) | Projeto Python/FastAPI no sentry.io |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | Endpoint de destino dos traces | Conexão OTLP no Grafana Cloud |
| `OTEL_EXPORTER_OTLP_HEADERS` | Header de autenticação do OTLP | Token gerado junto com a conexão OTLP |

Se qualquer uma dessas variáveis estiver vazia, a respectiva ferramenta simplesmente
não é ativada — não há erro, nem necessidade de alterar código.

## Checklist de verificação local

1. Preencha `SENTRY_DSN`, `OTEL_EXPORTER_OTLP_ENDPOINT` e `OTEL_EXPORTER_OTLP_HEADERS`
   no seu `.env`.
2. Rode `uvicorn app.main:app --reload`.
3. Acesse `http://localhost:8000/health` algumas vezes — deve responder `200`.
4. Force um erro em qualquer rota e confirme que ele aparece em Issues no Sentry.
5. Volte ao Grafana → Explore → datasource de traces → confirme que aparecem traces
   com `service.name = backend-eventos`.
