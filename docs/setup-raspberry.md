# Setup do Raspberry Pi

[← Voltar ao README](../README.md)

Instalação completa do **Livestream Orchestrator** num Raspberry Pi 3B+ com Debian 12 Bookworm (armhf).

Premissas:
- Câmera IP entrega RTSP **H.264** (Baseline, Main ou High até nível 4.2)
- Pipeline é **remux puro** (`-c:v copy -c:a copy`) — não há re-encode
- Stack roda via `docker-compose.yml` único na raiz do repositório (app + restreamer + cloudflared)

---

## Pré-requisitos

- Raspberry Pi 3B+ com Debian 12 instalado e acesso à internet
- SD Card de no mínimo 16 GB (32 GB recomendado)
- Câmera IP H.264 na mesma rede local
- Projeto configurado no Google Cloud Console — ver [setup-google-cloud.md](setup-google-cloud.md)
- Tunnel criado no Cloudflare Zero Trust
- Acesso SSH ou terminal local ao Pi

---

## 1 — Preparar o sistema

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y ca-certificates curl gnupg git
```

### IP fixo (recomendado)

Edite `/etc/network/interfaces`:

```
auto eth0
iface eth0 inet static
    address 192.168.1.100
    netmask 255.255.255.0
    gateway 192.168.1.1
    dns-nameservers 1.1.1.1
```

Aplique:

```bash
sudo systemctl restart networking
```

---

## 2 — Instalar Docker

```bash
curl -fsSL https://get.docker.com | sh
sudo systemctl enable --now docker
sudo usermod -aG docker $USER
```

Logout/login (ou `newgrp docker`) e valide:

```bash
docker --version
docker compose version
docker run --rm hello-world
```

---

## 3 — Clonar o repositório

```bash
sudo mkdir -p /opt/livestream
sudo chown $USER:$USER /opt/livestream
cd /opt
git clone https://github.com/usuario/livestream-app.git livestream
cd livestream
```

---

## 4 — Configurar variáveis de ambiente

```bash
cp .env.example .env
nano .env
```

Preencher todas as variáveis obrigatórias — ver lista completa em `CLAUDE.md` e `.env.example`. Pontos críticos:

- `APP_PUBLIC_URL` — sem barra no final, deve bater **exatamente** com o URI cadastrado no Google Cloud Console
- `RESTREAMER_URL=http://restreamer:8080` — nome de serviço do Compose, não trocar
- `RTSP_URL` — testar antes (ver seção Validação abaixo)
- `APP_SECRET_KEY` — gerar com `python3 -c "import secrets; print(secrets.token_hex(32))"`

---

## 5 — Validar câmera RTSP antes de subir a stack

Confirme que a câmera entrega H.264:

```bash
docker run --rm jrottenberg/ffmpeg:4.4-alpine \
  ffprobe -v error -select_streams v:0 \
  -show_entries stream=codec_name,profile,level \
  -of default=noprint_wrappers=1 \
  "rtsp://usuario:senha@192.168.1.50:554/stream"
```

Saída esperada: `codec_name=h264`, perfil Baseline/Main/High, nível ≤ 42.

Se vier `hevc`/`h265`, **não é compatível** — reconfigure a câmera para H.264 (a pipeline é remux, sem re-encode).

---

## 6 — Subir a stack

```bash
docker compose up -d
docker compose ps
```

Esperado: containers `app`, `restreamer`, `cloudflared` em estado `Up`.

Logs:

```bash
docker compose logs -f app
docker compose logs -f restreamer
docker compose logs -f cloudflared
```

A porta `:3000` (FastAPI) fica acessível na rede local em `http://192.168.1.100:3000` e via tunnel em `APP_PUBLIC_URL`.

A porta `:8080` do Restreamer **não é exposta ao host** — acesso apenas pela rede interna do Compose, via `app`.

---

## 7 — Primeiro login

1. Abra `APP_PUBLIC_URL` no navegador
2. Clique em **Entrar com Google**
3. Use uma conta cadastrada como testadora no Google Cloud Console
4. Aceite as permissões do escopo `youtube`

Após o primeiro login, o `refresh_token` fica salvo em `app/data/users.json` — usuário não precisa autorizar de novo (até revogação manual ou 6 meses de inatividade).

---

## 8 — Operação

### Comandos diários

```bash
cd /opt/livestream

# Status
docker compose ps
docker stats

# Logs ao vivo
docker compose logs -f app

# Reiniciar só a app (libera lock preso, mantém Restreamer)
docker compose restart app

# Atualizar para nova versão publicada no Docker Hub
docker compose pull && docker compose up -d
```

### Monitorar temperatura

```bash
watch -n 2 vcgencmd measure_temp
```

Com remux puro a CPU fica em ~5–15% e a temperatura raramente passa de 60°C. Acima de 80°C investigue — não é esperado.

Verificar throttle:

```bash
vcgencmd get_throttled   # 0x0 = sem throttle
```

---

## 9 — Boot automático

O `restart: always` no `docker-compose.yml` já garante reinício dos containers. Para subir a stack inteira no boot do Pi sem login interativo:

```bash
sudo systemctl enable docker
```

Docker sobe no boot, Compose recupera os containers com `restart: always`.

---

## Problemas comuns

Ver [troubleshooting.md](troubleshooting.md).

---

_Última revisão: 2026-05-25._

