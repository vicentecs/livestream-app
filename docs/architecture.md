# Arquitetura do Sistema

## Decisões técnicas

### Por que FastAPI e não Flask ou Django?

FastAPI é assíncrono nativamente, o que é essencial aqui: as chamadas à YouTube API, ao Restreamer e ao Google OAuth são todas operações de I/O que se beneficiam de `async/await`. Flask seria síncrono por padrão. Django seria excessivo para um sistema sem banco relacional.

### Por que JSON file e não SQLite ou PostgreSQL?

O estado do sistema é simples: poucos usuários, um broadcast ativo por vez, tokens OAuth por usuário. Um `users.json` com leitura/escrita via `storage.py` é suficiente, não introduz dependências extras e é fácil de inspecionar e fazer backup. Se o projeto crescer, a migração para SQLite é direta.

### Por que a câmera foi configurada para H.264 e não H.265?

O YouTube aceita apenas H.264 na ingestão RTMP. Com câmera H.265, o Pi 3B+ teria que fazer re-encode em software (CPU 80–100%, risco de throttle térmico, queda de qualidade). Com câmera H.264, o FFmpeg usa `-c:v copy -c:a copy` — remux puro, sem re-encode, com CPU em ~5–15% e qualidade idêntica à saída da câmera. A escolha de H.264 na câmera é uma decisão de arquitetura deliberada para viabilizar o hardware.

### Por que o Restreamer como engine de vídeo e não FFmpeg direto?

O Restreamer resolve a camada de gerenciamento do processo FFmpeg com API REST, retentativas de reconexão, logs estruturados e uma UI de fallback. Gerenciar subprocess FFmpeg diretamente no Python seria reinventar essa roda com mais riscos de processo órfão e leak de recursos.

### Por que Cloudflare Tunnel e não port forwarding?

- Não expõe porta no roteador — sem IP público direto
- HTTPS gratuito e automático — obrigatório para OAuth do Google
- Proteção DDoS da Cloudflare inclusa
- Compatível com IP dinâmico do provedor

---

## Containers e comunicação

```
┌──────────────────────────────────────────────────────┐
│                  Docker Compose Stack                │
│                  rede: livestream-net                │
│                                                      │
│  ┌────────────────┐         ┌──────────────────────┐ │
│  │  cloudflared   │         │     restreamer       │ │
│  │                │         │  datarhei/rpi-latest │ │
│  │  tunnel token  │         │  porta interna: 8080 │ │
│  └───────┬────────┘         │  (não exposta host)  │ │
│          │                  └──────────┬───────────┘ │
│          │ http://app:3000             │             │
│          ▼                             │             │
│  ┌────────────────┐                    │             │
│  │      app       │────────────────────┘             │
│  │  FastAPI :3000 │  http://restreamer:8080          │
│  │  porta host:   │                                  │
│  │  3000          │                                  │
│  └────────────────┘                                  │
└──────────────────────────────────────────────────────┘

Portas expostas ao host/internet:
  :3000  → interface web (apenas rede local, ou via tunnel)

Portas internas apenas:
  :8080  → UI e API do Restreamer (não acessível externamente)

Saída para YouTube:
  RTMP egress do container restreamer → rtmp://a.rtmp.youtube.com/live2
  (conexão de saída, não precisa porta exposta no host)
```

---

## Fluxo de autenticação OAuth

```
Usuário                App (FastAPI)           Google OAuth
   │                        │                       │
   │  GET /auth/login        │                       │
   │───────────────────────►│                       │
   │                        │  redirect_uri gerada   │
   │  302 → accounts.google  │  com APP_PUBLIC_URL   │
   │◄───────────────────────│                       │
   │                        │                       │
   │  login Google          │                       │
   │───────────────────────────────────────────────►│
   │                        │                       │
   │  redirect /auth/callback?code=xxx              │
   │◄───────────────────────────────────────────────│
   │                        │                       │
   │  GET /auth/callback    │                       │
   │───────────────────────►│                       │
   │                        │  troca code por tokens │
   │                        │───────────────────────►│
   │                        │  access_token          │
   │                        │  refresh_token ◄───────│
   │                        │                       │
   │                        │  salva em users.json   │
   │  302 → /               │  cria cookie sessão   │
   │◄───────────────────────│                       │
```

---

## Fluxo completo da live

```
Usuário          App (FastAPI)      YouTube API       Restreamer
   │                  │                  │                 │
   │  POST /live/start│                  │                 │
   │─────────────────►│                  │                 │
   │                  │ liveBroadcasts   │                 │
   │                  │ .insert()        │                 │
   │                  │─────────────────►│                 │
   │                  │  broadcast_id ◄──│                 │
   │                  │                  │                 │
   │                  │ liveStreams       │                 │
   │                  │ .insert()        │                 │
   │                  │─────────────────►│                 │
   │                  │  stream_id       │                 │
   │                  │  stream_key ◄────│                 │
   │                  │                  │                 │
   │                  │ liveBroadcasts   │                 │
   │                  │ .bind()          │                 │
   │                  │─────────────────►│                 │
   │                  │                  │                 │
   │                  │  configura stream_key              │
   │                  │  inicia FFmpeg  ─────────────────►│
   │                  │                  │                 │
   │                  │ transition →     │                 │
   │                  │ "testing"        │                 │
   │                  │─────────────────►│                 │
   │                  │                  │                 │
   │                  │  polling streamStatus              │
   │                  │─────────────────►│                 │
   │                  │  active ◄────────│                 │
   │                  │                  │                 │
   │                  │ transition →     │                 │
   │                  │ "live" ──────────►                 │
   │                  │                  │                 │
   │  200 OK, live!  │                  │                 │
   │◄─────────────────│                  │                 │
   │                  │                  │                 │
   │  POST /live/stop │                  │                 │
   │─────────────────►│                  │                 │
   │                  │  para FFmpeg    ─────────────────►│
   │                  │ transition →     │                 │
   │                  │ "complete" ──────►                 │
   │  200 OK         │                  │                 │
   │◄─────────────────│                  │                 │
```

---

## Lock de stream

O Pi 3B+ suporta apenas um processo FFmpeg por vez. Com remux H.264 a carga é baixa (~5–15% CPU), mas dois streams simultâneos ainda saturariam a largura de banda de upload e a interface de rede. O lock é um campo booleano `stream_locked` em memória (não persistido no JSON) gerenciado por `middleware.py`.

```
POST /live/start
    │
    ├── stream_locked == True?
    │       └── 409 Conflict: "Stream em uso por outro usuário"
    │
    └── stream_locked == False?
            └── set stream_locked = True
                inicia pipeline (remux H.264 → RTMP)
                salva broadcast_ids no users.json

POST /live/stop
    └── para pipeline
        set stream_locked = False
        limpa broadcast_ids do usuário
```

O lock é liberado também se o processo FFmpeg morrer inesperadamente (detectado por health check periódico no Restreamer).

---

## Renovação automática de token

O access token do Google expira em 1 hora. A renovação é transparente:

```python
# em auth.py — executado antes de qualquer chamada à YouTube API
if token_expiry < now + timedelta(minutes=5):
    credentials.refresh(Request())
    storage.update_tokens(user_email, credentials)
```

O `refresh_token` não expira, mas é revogado se o usuário remover o acesso em myaccount.google.com ou se o app ficar inativo por 6 meses (limite do Google para apps em modo de teste).
