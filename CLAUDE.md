# CLAUDE.md — Livestream Orchestrator

Contexto permanente do projeto para Claude Code. Leia este arquivo antes de qualquer tarefa.

---

## O que é este projeto

Sistema de live streaming que captura vídeo RTSP H.264 de câmera IP e transmite ao vivo no YouTube. Roda em um **Raspberry Pi 3B+ com Debian 12 (armhf)**. Múltiplos usuários autenticam com Google OAuth e iniciam lives em seus próprios canais do YouTube. O controle é feito via interface web acessível localmente e pela internet via Cloudflare Tunnel.

**Repositório:** github.com/vicentecs/livestream-app
**Imagem Docker:** vicentecs/livestream-app (Docker Hub)
**Documentação completa:** ver `docs/`

---

## Stack e dependências

| Camada | Tecnologia |
|---|---|
| Runtime | Python 3.11 |
| Framework web | FastAPI + Uvicorn |
| Autenticação | Google OAuth 2.0 (`google-auth-oauthlib`) |
| YouTube API | `google-api-python-client` |
| Sessões | `itsdangerous` (cookie assinado) |
| Storage | JSON file (`app/data/users.json`) |
| Streaming engine | datarhei Restreamer (container separado) |
| Infra | Docker Compose, Cloudflare Tunnel |
| CI/CD | GitHub Actions → Docker Hub (multi-arch: arm/v7, arm64, amd64) |
| Hardware alvo | Raspberry Pi 3B+ — ARM Cortex-A53, VideoCore IV |

---

## Estrutura do projeto

```
/
├── CLAUDE.md                  # este arquivo
├── docker-compose.yml         # stack completa (restreamer + app + cloudflared)
├── .env.example               # template de variáveis de ambiente
├── .gitignore
├── README.md
│
├── .claude/
│   └── commands/              # comandos customizados Claude Code
│       ├── add-route.md
│       ├── add-user.md
│       └── check-env.md
│
├── app/                       # código da aplicação Python
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── main.py                # FastAPI app, rotas, inicialização
│   ├── auth.py                # fluxo OAuth Google (login, callback, logout)
│   ├── youtube.py             # YouTube Data API (criar/encerrar broadcast)
│   ├── restreamer.py          # cliente HTTP da API REST do Restreamer
│   ├── storage.py             # leitura/escrita persistente de users.json
│   ├── models.py              # Pydantic models (User, BroadcastState, Config)
│   ├── middleware.py          # auth guard, lock de encoder, logging
│   ├── data/
│   │   └── users.json         # NÃO commitar — gerado em runtime
│   └── static/
│       └── index.html         # frontend HTML/JS/CSS (single file)
│
├── docs/
│   ├── architecture.md        # decisões de arquitetura e diagramas
│   ├── api.md                 # referência das rotas FastAPI
│   ├── setup-google-cloud.md  # passo a passo Google Cloud Console
│   ├── setup-raspberry.md     # instalação no Pi (Docker, Compose)
│   └── troubleshooting.md     # problemas comuns e soluções
│
└── .github/
    └── workflows/
        └── docker-publish.yml # CI/CD build multi-arch → Docker Hub
```

---

## Comandos essenciais

```bash
# Desenvolvimento local (x86)
docker compose up -d
docker compose logs -f app
docker compose logs -f restreamer

# Rebuildar a imagem da app
docker compose build app
docker compose up -d app

# Reiniciar só a app sem recriar o Restreamer
docker compose restart app

# Ver estado dos containers
docker compose ps
docker stats

# Acessar shell da app para debug
docker compose exec app bash

# Monitorar temperatura no Pi
watch -n 2 vcgencmd measure_temp

# Atualizar imagem no Pi após novo deploy
docker compose pull && docker compose up -d
```

---

## Variáveis de ambiente obrigatórias

Todas definidas no `.env` (nunca commitar). Ver `.env.example` como referência.

| Variável | Descrição |
|---|---|
| `GOOGLE_CLIENT_ID` | Client ID do projeto no Google Cloud Console |
| `GOOGLE_CLIENT_SECRET` | Client Secret do projeto no Google Cloud Console |
| `APP_SECRET_KEY` | String aleatória longa para assinar cookies de sessão |
| `APP_PUBLIC_URL` | URL pública via Cloudflare (ex: `https://live.seudominio.com`) |
| `RESTREAMER_URL` | URL interna do Restreamer (sempre `http://restreamer:8080`) |
| `RESTREAMER_USER` | Usuário admin do Restreamer |
| `RESTREAMER_PASS` | Senha admin do Restreamer |
| `RTSP_URL` | URL da câmera IP (ex: `rtsp://user:pass@192.168.1.50:554/stream`) |
| `CLOUDFLARE_TUNNEL_TOKEN` | Token do tunnel no Cloudflare Zero Trust |

---

## Regras de código

- Python 3.11+, type hints obrigatórios em todas as funções
- Async/await em todas as rotas FastAPI e chamadas HTTP externas
- `httpx` (não `requests`) para chamadas HTTP assíncronas
- Nunca logar tokens OAuth, stream keys ou senhas — usar `***` no lugar
- Toda interação com a YouTube API vai por `youtube.py` — não chamar diretamente de outras partes
- Toda interação com o Restreamer vai por `restreamer.py`
- `storage.py` é o único módulo que lê/escreve `users.json`
- O lock de encoder (um stream por vez) é gerenciado em `middleware.py`
- Erros da YouTube API devem ser tratados individualmente por código de status

---

## Restrições críticas de hardware

- **ARM32 (armhf)** — todas as imagens Docker devem incluir `linux/arm/v7`
- **Um stream por vez** — o Pi 3B+ não consegue processar dois streams simultâneos
- **Pipeline: remux sem re-encode** — a câmera entrega H.264; o FFmpeg usa `-c:v copy -c:a copy` para encaminhar o stream diretamente ao YouTube sem re-encode, mantendo CPU ~5–15%
- **Nunca forçar re-encode desnecessariamente** — não usar `libx264` na pipeline principal; só em casos de incompatibilidade de perfil/nível detectada em runtime
- **Temperatura:** acima de 80°C o Pi faz throttle — com remux o risco é baixo, mas monitorar em produção

---

## Fluxo OAuth — pontos de atenção

1. O `redirect_uri` enviado ao Google deve ser exatamente `APP_PUBLIC_URL + /auth/callback`
2. O `refresh_token` só é retornado na **primeira** autorização — armazenar imediatamente
3. Para forçar novo `refresh_token`: revogar acesso em myaccount.google.com e refazer login
4. Tokens expiram em 1 hora — `auth.py` deve renovar automaticamente via refresh token
5. Usuários precisam estar na lista de testadores no Google Cloud Console

---

## Fluxo da live — sequência obrigatória

```
1. liveBroadcasts.insert        → cria broadcast (monitorStream=false), obtém broadcast_id
2. liveStreams.insert            → cria stream, obtém stream_id + stream_key
3. liveBroadcasts.bind          → vincula broadcast + stream
4. Restreamer: configurar       → passa stream_key, inicia FFmpeg
5. aguardar streamStatus=active → polling até câmera conectar
6. liveBroadcasts.transition    → status: "live"

Encerramento:
7. Restreamer: parar            → FFmpeg encerrado
8. liveBroadcasts.transition    → status: "complete"
```

> ⚠️ Transição `"testing"` NÃO é usada. Broadcast é criado com `monitorStream.enableMonitorStream=false`, então YouTube vai direto de `ready` → `live`. Chamar `transition("testing")` nessa config retorna `403 invalidTransition`. Para habilitar fase de testing, ligar monitor stream no insert e adicionar transição antes do `live`.

---

## Não fazer

- Não expor a porta 8080 do Restreamer para o host
- Não commitar `.env`, `users.json` ou qualquer arquivo com credenciais
- Não usar `requests` (síncrono) — usar `httpx` com `async`
- Não iniciar segundo stream se `stream_locked == True`
- Não hardcodar URLs, credenciais ou stream keys no código
- Não usar `pip install` sem `--no-cache-dir` no Dockerfile
