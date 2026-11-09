# Observabilidade

Este documento explica a stack de observabilidade do backend: o que cada ferramenta
faz, onde o código de integração fica, como configurar do zero, como correlacionar
log, resposta HTTP e Sentry pelo `request_id`, e o que ainda não está coberto.

> Nenhum DSN, token ou ID real aparece neste documento. Onde for necessário um valor
> de configuração, use `.env.example` como referência e gere as suas próprias
> credenciais nos passos descritos abaixo.

> Regra deste documento: ele só afirma o que está implementado. O que está pendente ou
> não foi validado aparece em [Limitações conhecidas](#limitações-conhecidas) e em
> [Follow-ups](#follow-ups).

## Visao geral

| Necessidade | Ferramenta | O que resolve |
|---|---|---|
| Erros em produção | **Sentry** | Captura exceções não tratadas e logs de nível ERROR, com stack trace, contexto da requisição e agrupamento automático de issues |
| Logs | **structlog** | Logs em JSON estruturado (em vez de texto livre), fáceis de filtrar e buscar |
| Correlação | **`X-Request-ID`** | O mesmo `request_id` no header da resposta, em todo log da requisição e na tag do Sentry |
| Performance e tracing distribuído | **OpenTelemetry → Grafana Cloud** | Latência por endpoint, volume de chamadas, rastreio de uma requisição ponta a ponta |
| Disponibilidade | **`/health`** | Endpoint simples para checagem externa (uptime monitors) |

Todas as ferramentas sao open source (ou rodam sobre software open source com tier
gratuito) e funcionam em modo **push** — ou seja, o proprio processo da API envia os
dados para fora no momento em que algo acontece. Isso é importante porque o backend
roda como **function serverless na Vercel** ([vercel.json](../vercel.json)): nao existe
um processo de longa duracao no ar para ser "raspado" (scrape) por ferramentas como
Prometheus tradicional — por isso essas 3 ferramentas foram escolhidas especificamente
por serem compativeis com esse modelo.

Ordem de inicialização em [app/main.py](../app/main.py):

1. `setup_logging()`
2. `setup_sentry()`
3. `FastAPI(...)`
4. `setup_telemetry(app)` (OpenTelemetry, independente do Sentry)

## Request ID e correlação

**O que é:** cada requisição recebe um identificador (`request_id`). O mesmo valor sai
no header `X-Request-ID` da resposta, em todos os logs emitidos durante a requisição e
na tag `request_id` do Sentry. Com ele, a partir de uma resposta (ou de um print de
erro do front) é possível achar os logs e o evento do Sentry daquela requisição.

**Onde fica o código:** `RequestIdMiddleware` em [app/core/middleware.py](../app/core/middleware.py),
registrado em [app/main.py](../app/main.py).

**Regras do ID:**
- Se o cliente envia `X-Request-ID` e o valor faz `fullmatch` em `[A-Za-z0-9._-]{1,128}`,
  o valor é reaproveitado. Caso contrário, é gerado um `uuid4`.
- O ID é decidido **uma única vez**, no middleware.
- Se um endpoint colocar seu próprio `X-Request-ID` na resposta, o header é removido e
  substituído pelo do middleware (nunca sai duplicado).
- O valor também fica em `request.state.request_id`, em endpoints `async` e `sync`.
- Preflight (`OPTIONS`), 404, 422 e 429 também recebem o header.

**Como o contexto é propagado:**
- Middleware ASGI puro (não usa `BaseHTTPMiddleware`).
- No **início** de cada requisição, o middleware chama `clear_contextvars()` e vincula
  `request_id`, `method` e `path` às contextvars do structlog. A limpeza é no início
  (e não no fim) para que um log de erro emitido depois ainda herde o `request_id`.
- No Sentry, o middleware chama `sentry_sdk.set_tag("request_id", ...)`.

### Ordem dos middlewares e CORS

`app.user_middleware == ['RequestIdMiddleware', 'CORSMiddleware']`.

No Starlette, o **último** `add_middleware` é o mais **externo**. Aqui o
`RequestIdMiddleware` é registrado depois do CORS no código, então, na **execução**, ele
roda antes do CORS. Foi isso que a issue pediu ("antes do CORS" = ordem de execução).

O CORS usa `expose_headers=["X-Request-ID"]`. Sem isso o navegador não deixa o
JavaScript do front ler o header da resposta. Todas as respostas CORS levam
`Vary: Origin`.

### Como correlacionar log ↔ header ↔ Sentry

1. Pegue o `X-Request-ID` da resposta (ou do print do erro).
2. **Logs:** filtre o campo `request_id` com esse valor. Aparecem o `http.request.completed`
   e qualquer outro log emitido durante a requisição.
3. **Sentry:** busque pela tag `request_id:<valor>`. Logs de nível INFO da requisição
   chegam como breadcrumbs do evento; logs ERROR e exceções não tratadas viram eventos.

## Logs estruturados (structlog)

**O que é:** em vez de logs em texto livre, os logs saem em JSON. Isso facilita filtrar
e buscar logs em ferramentas de agregação. O handler do logging da stdlib usa o
`ProcessorFormatter` do structlog, então logs da stdlib (por exemplo `uvicorn.error`) e
logs do structlog saem no mesmo formato.

**Onde fica o código:** [app/core/logging.py](../app/core/logging.py), função
`setup_logging()`.

### Contrato de campos

| Quando | Campos |
|---|---|
| Sempre | `timestamp` (ISO 8601, UTC), `level` (maiúsculo), `event`, `logger`, `service`, `environment` |
| Se houver exceção | `exception` (traceback) |
| Via middleware (contextvars) | `request_id`, `method`, `path` |
| Só no `http.request.completed` | `status_code`, `duration_ms` e, se existir, `user_id` |

### Log de acesso: `http.request.completed`

O middleware emite **um** log por requisição, com `event: "http.request.completed"`:

- Nível `info`, emitido ao enviar o último body da resposta (uma flag evita duplicar).
- `path` não inclui a query string.
- `duration_ms` vai do início da requisição até o último body. **Não** espera
  `BackgroundTask`.
- `user_id` é opcional e aparece só neste log. É um identificador opaco, nunca dado
  pessoal. Preencher esse campo (a dependency de auth) não faz parte desta task.
- O `uvicorn.access` está **silenciado** (`propagate = False` com `NullHandler`). O
  `http.request.completed` é a única linha de acesso. Os loggers `uvicorn` e
  `uvicorn.error` continuam propagando (startup e erros do servidor).

Exemplo real (saída do app para `GET /docs` com `X-Request-ID: demo-456`). A ordem dos
campos no JSON não é garantida:

```json
{"status_code": 200, "duration_ms": 1.0, "event": "http.request.completed", "request_id": "demo-456", "path": "/docs", "method": "GET", "logger": "app.core.middleware", "level": "INFO", "timestamp": "2026-11-07T02:30:28.981746Z", "service": "eventos-backend-api", "environment": "development"}
```

**Como ver os logs:**
- Localmente: aparecem na saída do processo (terminal do `uvicorn`, ou
  `docker compose logs api --no-log-prefix`).
- Em produção: `vercel logs <nome-do-projeto>` (CLI da Vercel) ou a aba "Logs" no
  dashboard do projeto na Vercel.

**Como adicionar um log novo em qualquer lugar do código:**

Em qualquer módulo de `app/` (router, service, repository), basta criar o logger e usá-lo.
Não é preciso configurar nada no arquivo: a configuração do JSON e dos campos fixos é
global e acontece uma vez, em `setup_logging()`, na subida do app.

```python
import structlog

logger = structlog.get_logger(__name__)

# Exemplo ilustrativo: `evento` e `user_id` precisam existir no escopo onde você loga,
# por exemplo dentro de um service que recebeu o evento e o usuário.
logger.info("evento_criado", evento_id=evento.id, criado_por=user_id)
```

Os pares chave-valor (`evento_id`, `criado_por`) entram como campos no JSON, junto com os
campos fixos do contrato (`timestamp`, `level`, `event`, `logger`, `service`,
`environment`). O valor de `__name__` vira o campo `logger`, por exemplo
`app.services.evento_service`.

Dentro de uma requisição, `request_id`, `method` e `path` entram sozinhos, pelas
contextvars que o `RequestIdMiddleware` vincula no início da requisição. Não passe esses
campos na chamada do log.

Fora de uma requisição (por exemplo, no startup do app), não há contexto vinculado, então
o log sai sem `request_id`, `method` e `path`.

O campo `user_id` do contrato é diferente dos campos livres do exemplo: ele só aparece no
`http.request.completed`, e só quando a requisição fornece o identificador. Para campos
próprios, use nomes que não colidam com os do contrato.

## Sentry (rastreamento de erros)

**O que é:** ferramenta que captura excecoes automaticamente, mostra o stack trace
completo, o contexto da requisicao que falhou, e agrupa erros parecidos na mesma
"issue" para nao gerar ruido repetido.

**Onde fica o código:**
- Inicialização: `setup_sentry()` em [app/core/telemetry.py](../app/core/telemetry.py),
  chamada em [app/main.py](../app/main.py) antes de `FastAPI(...)`.
- Configuração: `SENTRY_DSN` e `ENVIRONMENT` em [app/core/config.py](../app/core/config.py).

**O que `setup_sentry()` faz:**
- Sem `SENTRY_DSN`, não inicializa (nenhuma mudança de comportamento, nenhum erro).
- Se o `sentry_sdk` não estiver instalado, registra um aviso e segue.
- Inicializa com `environment=settings.ENVIRONMENT` e `traces_sample_rate=0.1`.

**Como configurar:**
1. Crie uma conta gratuita em [sentry.io](https://sentry.io).
2. Crie um projeto novo escolhendo a plataforma **Python → FastAPI**.
3. Copie o DSN gerado (formato `https://<chave>@<org>.ingest.<regiao>.sentry.io/<id>`).
4. Localmente: cole em `SENTRY_DSN=` no seu `.env` (nunca commite esse arquivo).
5. Em produção (Vercel): Settings → Environment Variables → adicione `SENTRY_DSN` com
   o mesmo valor, marcando o ambiente "Production".
6. `ENVIRONMENT` aceita `development`, `preview` ou `production` (padrão:
   `development`). Também é lido de `VERCEL_ENV`, que a Vercel define.

**Como verificar que está funcionando:**
1. Rode a API com `SENTRY_DSN` preenchido.
2. Force uma exceção (por exemplo, adicione temporariamente um `raise Exception("teste sentry")`
   em uma rota).
3. No painel do Sentry, abra o projeto → **Issues**: o erro deve aparecer em poucos
   segundos, com stack trace e a tag `environment` igual ao valor de `ENVIRONMENT`.
   Esse `environment` foi conferido no painel com `development`. A tag `request_id`
   também foi conferida no painel, no evento de um 500 não tratado (campo **Tags**), e
   o `request_id` aparece nos breadcrumbs desse evento.

**Taxa de amostragem:** `traces_sample_rate=0.1` (10% das requisições geram dados de
performance). Por isso a maior parte dos eventos que chegam no Sentry são *transactions*.
Erros não são amostrados desta forma.

**O que vira evento:** um `logger.exception` / log de nível ERROR vira evento de erro
(integração de logging do `sentry-sdk`, `event_level` padrão ERROR), e um 500 não
tratado gera um evento de exceção.

## OpenTelemetry + Grafana Cloud (traces e performance)

**O que é:** tracing distribuído. Cada requisição HTTP gera um "trace": uma linha do
tempo de quanto tempo cada parte levou. Isso permite ver, endpoint por endpoint, qual
está lento e por quê.

**Onde fica o código:** [app/core/telemetry.py](../app/core/telemetry.py), função
`setup_telemetry(app)`, chamada em [app/main.py](../app/main.py) logo após a criação do
`FastAPI()`. Ela:
1. Só ativa se `settings.OTEL_EXPORTER_OTLP_ENDPOINT` estiver preenchido (senão, não
   faz nada).
2. Exporta `OTEL_EXPORTER_OTLP_ENDPOINT` e `OTEL_EXPORTER_OTLP_HEADERS` para
   `os.environ`, porque o SDK do OpenTelemetry lê essas variáveis do ambiente.
3. Cria um `TracerProvider` com `service.name = backend-eventos`, adiciona um
   `BatchSpanProcessor` com o `OTLPSpanExporter` (HTTP) e registra como provider global.

O parâmetro `app` não é usado dentro da função. **A função não chama
`FastAPIInstrumentor.instrument_app(app)`**: o pacote
`opentelemetry-instrumentation-fastapi` está nas dependências, mas nenhum código do
`app/` o invoca. Os spans das rotas vêm do que o FastAPI já emite por conta própria
(ver [Limitações conhecidas](#limitações-conhecidas) para o que não foi validado).

**O OpenTelemetry não participa da correlação por `request_id`.** O `trace_id` não está
nos logs; a correlação descrita neste documento é só por `request_id`.

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
4. A tabela de resultados mostra as requisições recentes, com duração em milissegundos.

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
| `ENVIRONMENT` | Valor do campo `environment` nos logs e no Sentry. Aceita `development`, `preview`, `production`. Padrão: `development`. Também lê `VERCEL_ENV` | Definida por você; na Vercel, `VERCEL_ENV` já vem pronta |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | Endpoint de destino dos traces | Conexão OTLP no Grafana Cloud |
| `OTEL_EXPORTER_OTLP_HEADERS` | Header de autenticação do OTLP | Token gerado junto com a conexão OTLP |

Se `SENTRY_DSN` ou `OTEL_EXPORTER_OTLP_ENDPOINT` estiverem vazias, a respectiva
ferramenta não é ativada, sem erro e sem necessidade de alterar código.

## Checklist de verificação local

1. Preencha `SENTRY_DSN`, `OTEL_EXPORTER_OTLP_ENDPOINT` e `OTEL_EXPORTER_OTLP_HEADERS`
   no seu `.env`.
2. Suba a API (`uvicorn app.main:app --reload` ou `docker compose up -d api`) e espere o
   servidor aceitar conexões.
3. Acesse `http://localhost:8000/health` algumas vezes — deve responder `200`.
4. Faça uma requisição com ID próprio e confira que o mesmo valor volta no header:
   `curl -i -H "X-Request-ID: demo-123" http://localhost:8000/docs`
5. Procure `demo-123` nos logs: deve haver uma linha `http.request.completed` com
   `"request_id": "demo-123"`, e nenhuma linha do `uvicorn.access`.
6. Force um erro em qualquer rota e confirme que ele aparece em Issues no Sentry.
7. Volte ao Grafana → Explore → datasource de traces e confirme se aparecem traces com
   `service.name = backend-eventos`.

## Limitações conhecidas

- **Erro não tratado (500) sai sem `X-Request-ID` e sem headers CORS.** O handler de
  `Exception` roda no `ServerErrorMiddleware`, **por fora** dos middlewares de usuário
  (`RequestIdMiddleware` e `CORSMiddleware`). Em um teste com `TestClient`, comparado
  a uma rota que responde 200, o 500 voltou sem `x-request-id`,
  `access-control-expose-headers`, `access-control-allow-credentials` e `vary`. Na
  prática, quem chama não vê o ID, e o navegador não consegue ler a resposta de um
  front em outra origem. O `request_id` continua presente no log de erro, no
  `http.request.completed` e no evento do Sentry. A correção estrutural (middleware
  interno que converta exceções em resposta) é follow-up.
- **`duration_ms` não inclui `BackgroundTask`.** O tempo é medido até o último body.
- **Status 500 assumido.** Se a resposta não passa pelo `send` do middleware, o
  `http.request.completed` registra `status_code: 500`.
- **Ordem dos logs no 500.** No `TestClient`, o `http.request.completed` saiu antes do
  log "Unhandled exception". Foi observado só no `TestClient`, não sob o uvicorn.
- **OpenTelemetry não validado ponta a ponta.** O FastAPI (a partir da 0.142, segundo a
  documentação dele) emite traces nativamente e usa os providers globais configurados
  antes de o app iniciar. Aqui o provider é registrado **depois** de `FastAPI(...)`. Não
  foi validado que os spans chegam ao Grafana por esse caminho, nem se há exportação em
  duplicidade (o FastAPI também lê `OTEL_EXPORTER_OTLP_ENDPOINT` do ambiente).
- **Serverless não validado.** Não foi validado se logs podem se perder quando o runtime
  da Vercel congela o processo logo após a resposta.
- **`trace_id` não está nos logs.** Não há correlação log ↔ trace.

## Follow-ups

Itens identificados e fora do escopo desta task:

- Middleware interno que converta exceções não tratadas em resposta, para o 500 levar
  `X-Request-ID` e CORS.
- Validar o OpenTelemetry ponta a ponta (spans no Grafana, ordem do provider, exportação
  duplicada) e decidir o destino do pacote `opentelemetry-instrumentation-fastapi`.
- Remover o campo `color_message` (códigos ANSI) dos logs do uvicorn.
- Teste automatizado para `uvicorn.access` silenciado (`propagate is False`).
- Ruído do Sentry nos testes (`SENTRY_DSN=""` no `conftest` raiz).
- `StarletteDeprecationWarning` (`httpx` → `httpx2`).
- Fixture `json_logging` duplicada e `asyncio_default_fixture_loop_scope` não definido
  no `pytest-asyncio`.
- Antes de subir o nível do `http.request.completed` para 5xx, validar o comportamento
  do `LoggingIntegration` na documentação do Sentry.

