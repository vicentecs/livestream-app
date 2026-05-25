# Livestream Orchestrator

Sistema de live streaming multi-usuário para Raspberry Pi 3B+. Captura vídeo RTSP H.264 de câmera IP e transmite ao vivo no YouTube via remux (sem re-encode), com autenticação Google OAuth e controle via interface web.

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
  Browser (usuário)
  https://live.seudominio.com
```

## Funcionalidades

- Login com conta Google (OAuth 2.0)
- Criação automática de live no YouTube via API
- Controle de start/stop pela interface web
- Suporte a múltiplos usuários (um encoder por vez)
- Acessível localmente e pela internet via Cloudflare Tunnel
- CI/CD automático via GitHub Actions → Docker Hub

## Requisitos

- Raspberry Pi 3B+ com Debian 12 (Bookworm)
- Docker e Docker Compose instalados
- Câmera IP com stream RTSP H.264 (Baseline, Main ou High até nível 4.2)
- Conta Google com canal YouTube habilitado para live
- Projeto configurado no Google Cloud Console
- Domínio com Cloudflare (para o Tunnel)

## Instalação rápida

```bash
# 1. Clonar o repositório
git clone https://github.com/usuario/livestream-app.git
cd livestream-app

# 2. Configurar variáveis de ambiente
cp .env.example .env
nano .env  # preencher todas as variáveis

# 3. Subir a stack
docker compose up -d

# 4. Verificar status
docker compose ps
docker compose logs -f app
```

Acesse `http://IP-DO-PI:3000` ou `https://live.seudominio.com`.

## Documentação

| Documento | Descrição |
|---|---|
| [Arquitetura](docs/architecture.md) | Decisões técnicas e diagramas |
| [API Reference](docs/api.md) | Rotas FastAPI |
| [Setup Google Cloud](docs/setup-google-cloud.md) | Configurar OAuth e YouTube API |
| [Setup Raspberry Pi](docs/setup-raspberry.md) | Instalação completa no Pi |
| [Troubleshooting](docs/troubleshooting.md) | Problemas comuns |

## Desenvolvimento

```bash
# Build local
docker compose build app

# Logs em tempo real
docker compose logs -f

# Shell na app
docker compose exec app bash

# Atualizar no Pi após deploy
docker compose pull && docker compose up -d
```

## Licença

MIT
