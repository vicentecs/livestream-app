# API Reference

Base URL local: `http://IP-DO-PI:3000`  
Base URL pública: `https://live.seudominio.com`

Todas as rotas protegidas exigem sessão autenticada (cookie `session`). Rotas não autenticadas redirecionam para `/auth/login`.

---

## Autenticação

### `GET /auth/login`
Inicia o fluxo OAuth. Redireciona para a tela de login do Google.

**Response:** `302 → accounts.google.com/o/oauth2/...`

---

### `GET /auth/callback`
Callback OAuth. Recebe o `code` do Google, troca por tokens, cria sessão.

**Query params:**
- `code` — código de autorização (enviado pelo Google)
- `state` — CSRF token (validado internamente)

**Response sucesso:** `302 → /`  
**Response erro:** `302 → /?error=auth_failed`

---

### `POST /auth/logout`
Encerra a sessão local. Não revoga o token no Google.

**Response:** `302 → /`

---

## Status

### `GET /status`
Retorna estado atual do sistema.

**Auth:** obrigatória

**Response `200`:**
```json
{
  "stream_locked": false,
  "active_user": null,
  "current_user": {
    "email": "usuario@gmail.com",
    "name": "Nome do Usuário"
  },
  "broadcast": null
}
```

**Response quando live ativa:**
```json
{
  "stream_locked": true,
  "active_user": "usuario@gmail.com",
  "current_user": {
    "email": "usuario@gmail.com",
    "name": "Nome do Usuário"
  },
  "broadcast": {
    "broadcast_id": "abc123",
    "stream_id": "xyz789",
    "youtube_url": "https://youtu.be/abc123",
    "started_at": "2026-05-24T14:00:00Z",
    "uptime_seconds": 3600
  }
}
```

---

## Controle da Live

### `POST /live/start`
Inicia a live: cria broadcast no YouTube e inicia o Restreamer.

**Auth:** obrigatória  
**Stream livre:** obrigatório (retorna 409 se ocupado)

**Body (opcional):**
```json
{
  "title": "Minha Live",
  "description": "Descrição da live",
  "privacy": "public"
}
```

Campos opcionais — defaults: título com data/hora atual, privacidade `public`.

**Response `200`:**
```json
{
  "status": "started",
  "broadcast_id": "abc123",
  "youtube_url": "https://youtu.be/abc123"
}
```

**Response `409` — stream ocupado:**
```json
{
  "error": "stream_busy",
  "message": "O stream está em uso por outro usuário.",
  "active_user": "outro@gmail.com"
}
```

**Response `502` — falha no Restreamer ou YouTube API:**
```json
{
  "error": "upstream_error",
  "message": "Falha ao iniciar o FFmpeg.",
  "detail": "..."
}
```

---

### `POST /live/stop`
Encerra a live: para o Restreamer e finaliza o broadcast no YouTube.

**Auth:** obrigatória  
**Restrição:** só o usuário que iniciou a live pode encerrá-la (ou admin)

**Response `200`:**
```json
{
  "status": "stopped",
  "broadcast_id": "abc123"
}
```

**Response `404` — nenhuma live ativa:**
```json
{
  "error": "no_active_broadcast",
  "message": "Nenhuma live em andamento."
}
```

---

## Configuração

### `GET /config`
Retorna configuração atual (sem dados sensíveis).

**Auth:** obrigatória

**Response `200`:**
```json
{
  "rtsp_url_masked": "rtsp://***@192.168.1.50:554/stream",
  "ffmpeg_preset": "ultrafast",
  "resolution": "1280x720",
  "video_bitrate_kbps": 2500,
  "audio_bitrate_kbps": 128,
  "framerate": 25
}
```

---

## Health

### `GET /health`
Verifica status dos serviços dependentes. Não exige autenticação.

**Response `200`:**
```json
{
  "app": "ok",
  "restreamer": "ok",
  "restreamer_ffmpeg": "idle"
}
```

**Response `503` — Restreamer inacessível:**
```json
{
  "app": "ok",
  "restreamer": "unreachable",
  "restreamer_ffmpeg": "unknown"
}
```

---

## Códigos de erro padronizados

| Código | Significado |
|---|---|
| `auth_required` | Sessão não encontrada ou expirada |
| `token_expired` | Token Google expirado e não renovável |
| `stream_busy` | Outro usuário está transmitindo |
| `no_active_broadcast` | Nenhuma live em andamento |
| `upstream_error` | Falha na YouTube API ou Restreamer |
| `permission_denied` | Usuário não tem permissão para a ação |
