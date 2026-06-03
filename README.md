# Livestream Orchestrator

> 🚧 Em desenvolvimento — docs prontas, código em andamento.

Sistema pessoal de live streaming para Raspberry Pi 3B+. Captura RTSP H.264 da câmera IP e transmite no YouTube via remux (sem re-encode), com login Google OAuth e controle via web.

## Visão geral

```
Câmera IP (H.264 RTSP)
        │
        ▼
  Raspberry Pi 3B+
  ┌─────────────────────────────────────┐
  │  Docker Compose                     │
  │                                     │
  │  ┌─────────────┐  ┌─────────────┐  │
  │  │ Orquestrador│  │ Restreamer  │  │
  │  │  FastAPI    │──│  FFmpeg     │  │
  │  │  OAuth      │  │  remux      │  │
  │  │  YouTube API│  │  -c copy    │  │
  │  └─────────────┘  └──────┬──────┘  │
  │         ▲                │         │
  │  Cloudflare              ▼         │
  │  Tunnel            YouTube RTMP    │
  └─────────────────────────────────────┘
        │
        ▼
  Browser
  https://live.seudominio.com
```

Detalhes em [docs/architecture.md](docs/architecture.md).

## Pré-requisitos

| Item | Versão |
|---|---|
| Hardware | Raspberry Pi 3B+ (armhf) |
| SO | Debian 12 Bookworm |
| Docker | ≥ 24 + Compose V2 |
| Câmera IP | RTSP H.264 (Baseline/Main/High até nível 4.2) |
| Conta Google | Canal YouTube + projeto Google Cloud OAuth |
| Domínio Cloudflare | Tunnel configurado |

Setup OAuth: [docs/setup-google-cloud.md](docs/setup-google-cloud.md).

## Instalação

### Dependências

Instalar Git e Docker (com plugin Compose) no Debian/Raspberry Pi OS:

```bash
# Git
sudo apt update
sudo apt install -y git

# Docker Engine + Compose plugin (script oficial)
curl -fsSL https://get.docker.com | sudo sh

# Rodar docker sem sudo (relogar depois)
sudo usermod -aG docker $USER

# Verificar
git --version
docker --version
docker compose version
```

### Deploy

```bash
git clone https://github.com/vicentecs/livestream-app
cd livestream-app
cp .env.example .env
nano .env                    # preencher tudo
docker compose up -d
docker compose logs -f app
```

Passo a passo completo no Pi: [docs/setup-raspberry.md](docs/setup-raspberry.md).

Acesso: `http://IP-DO-PI:3000` ou `https://live.seudominio.com`.

## Variáveis de ambiente

Todas obrigatórias. Ver [.env.example](.env.example).

| Variável | Origem |
|---|---|
| `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` | Google Cloud Console |
| `APP_SECRET_KEY` | `python3 -c "import secrets; print(secrets.token_hex(32))"` |
| `APP_PUBLIC_URL` | URL do Cloudflare Tunnel (sem barra final) |
| `RESTREAMER_URL` | Sempre `http://restreamer:8080` |
| `RESTREAMER_USER` / `RESTREAMER_PASS` | Admin do Restreamer |
| `RTSP_URL` | URL RTSP da câmera |
| `CLOUDFLARE_TUNNEL_TOKEN` | Cloudflare Zero Trust → Tunnels |

## Comandos úteis

```bash
docker compose ps
docker compose logs -f app
docker compose restart app                  # libera lock preso
docker compose pull && docker compose up -d # atualizar
watch -n 2 vcgencmd measure_temp            # temperatura Pi
vcgencmd get_throttled                      # 0x0 = ok
```

## Documentação

| Doc | Conteúdo |
|---|---|
| [docs/architecture.md](docs/architecture.md) | Decisões técnicas, diagramas, fluxos |
| [docs/setup-google-cloud.md](docs/setup-google-cloud.md) | OAuth + YouTube API |
| [docs/setup-raspberry.md](docs/setup-raspberry.md) | Instalação no Pi |
| [docs/troubleshooting.md](docs/troubleshooting.md) | Problemas comuns |
| [CLAUDE.md](CLAUDE.md) | Contexto para Claude Code |
