# Guia de Instalação: Restreamer no Raspberry Pi 3B+ (Debian)

**Sistema:** Debian 12 Bookworm (armhf / 32-bit)  
**Software:** datarhei Restreamer via Docker  
**Objetivo:** Capturar RTSP H.264 de câmera IP e transmitir ao vivo no YouTube com controle via interface web local

---

## Pré-requisitos

- Raspberry Pi 3B+ com Debian 12 instalado e acesso à internet
- SD Card de no mínimo 16 GB (32 GB recomendado)
- Câmera IP na mesma rede local com RTSP habilitado
- Stream Key do YouTube (obtida no YouTube Studio → Go Live)
- Acesso SSH ou terminal local ao Pi

---

## Parte 1 — Preparar o sistema

### 1.1 Atualizar os pacotes

```bash
sudo apt update && sudo apt upgrade -y
```

### 1.2 Instalar dependências necessárias

```bash
sudo apt install -y ca-certificates curl gnupg lsb-release
```

### 1.3 Configurar IP fixo para o Pi (recomendado)

Edite o arquivo de configuração de rede:

```bash
sudo nano /etc/network/interfaces
```

Adicione ou edite a interface (substitua `eth0` por `wlan0` se for Wi-Fi):

```
auto eth0
iface eth0 inet static
    address 192.168.1.100
    netmask 255.255.255.0
    gateway 192.168.1.1
    dns-nameservers 8.8.8.8
```

> **Dica:** Escolha um IP fora da faixa de DHCP do seu roteador. Você vai acessar o Restreamer por esse IP, então é importante que não mude.

Aplique a configuração:

```bash
sudo systemctl restart networking
```

---

## Parte 2 — Instalar o Docker

### 2.1 Remover versões antigas (se houver)

```bash
for pkg in docker.io docker-doc docker-compose podman-docker containerd runc; do
    sudo apt remove -y $pkg 2>/dev/null
done
```

### 2.2 Instalar via script oficial do Docker

```bash
curl -fsSL https://get.docker.com | sh
```

> Esse script detecta automaticamente a arquitetura ARM e instala a versão correta.

### 2.3 Iniciar e habilitar o Docker no boot

```bash
sudo systemctl enable docker
sudo systemctl start docker
```

### 2.4 Permitir uso do Docker sem sudo

```bash
sudo usermod -aG docker $USER
```

> Faça logout e login novamente para o grupo ser aplicado, ou execute `newgrp docker` na sessão atual.

### 2.5 Verificar a instalação

```bash
docker --version
docker run hello-world
```

A saída deve mostrar a versão do Docker e "Hello from Docker!".

### 2.6 Instalar o Docker Compose plugin

```bash
sudo apt install -y docker-compose-plugin
docker compose version
```

---

## Parte 3 — Instalar o Restreamer

### 3.1 Criar os diretórios de dados persistentes

```bash
sudo mkdir -p /opt/restreamer/config
sudo mkdir -p /opt/restreamer/data
```

### 3.2 Criar o arquivo docker-compose.yml

```bash
sudo mkdir -p /opt/restreamer
sudo nano /opt/restreamer/docker-compose.yml
```

Cole o conteúdo abaixo:

```yaml
version: "3"

services:
  restreamer:
    image: datarhei/restreamer:rpi-latest
    container_name: restreamer
    restart: always
    privileged: true
    ports:
      - "8080:8080"   # Interface web HTTP
      - "8181:8181"   # Interface web HTTPS
      - "1935:1935"   # RTMP entrada
      - "1936:1936"   # RTMPS entrada
      - "6000:6000/udp" # SRT
    volumes:
      - /opt/restreamer/config:/core/config
      - /opt/restreamer/data:/core/data
```

> O `privileged: true` é necessário para acesso ao hardware de vídeo do Pi (VideoCore IV).

Salve com `Ctrl+X`, `Y`, `Enter`.

### 3.3 Subir o container

```bash
cd /opt/restreamer
docker compose up -d
```

O Docker vai baixar a imagem (~500 MB) e iniciar o container. Aguarde a conclusão do download.

### 3.4 Verificar se está rodando

```bash
docker ps
docker logs restreamer
```

Você deve ver o container `restreamer` com status `Up`.

---

## Parte 4 — Configuração inicial pelo navegador

### 4.1 Acessar a interface web

Em qualquer dispositivo na mesma rede, abra o navegador e acesse:

```
http://192.168.1.100:8080/ui
```

(substitua pelo IP fixo que você configurou)

### 4.2 Criar a conta de administrador

Na primeira execução, o Restreamer pede para criar login e senha. Escolha credenciais seguras — qualquer pessoa na rede local poderá acessar essa URL.

### 4.3 Configurar a fonte de vídeo (câmera IP)

1. Clique em **"Create my first video source"** (ou "Add video source")
2. Selecione o tipo **RTSP**
3. Insira a URL da sua câmera no formato:
   ```
   rtsp://usuario:senha@192.168.1.XX:554/stream
   ```
   > A URL exata depende da marca/modelo da câmera. Consulte o manual ou teste no VLC primeiro.
4. Em **Video**, selecione:
   - Codec de entrada: detectado automaticamente (H.264/HEVC)
   - Codec de saída: **H.264** (obrigatório para YouTube)
   - Preset: `ultrafast` (melhor performance no Pi 3)
   - Resolução: comece com **1920x1080**
   - Bitrate: **4500 kbps**
5. Em **Audio**: marque "Add silent audio track" se a câmera não tiver áudio (o YouTube exige uma faixa de áudio)
6. Clique em **Start**

### 4.4 Configurar o destino YouTube (Publication Service)

1. No painel do Restreamer, clique em **"Add publication service"**
2. Selecione **YouTube Live**
3. Insira sua **Stream Key** do YouTube Studio
4. Clique em **Start Publication**

---

## Parte 5 — Controle da live no dia a dia

A partir de agora, para iniciar ou parar a transmissão:

1. Acesse `http://192.168.1.100:8080/ui` de qualquer dispositivo na rede
2. Use o botão **Play/Stop** na tela principal para controlar a fonte de vídeo
3. Use o botão **Play/Stop** na seção de Publication Services para controlar o envio ao YouTube
4. O painel mostra em tempo real: status, bitrate, viewers e uptime

---

## Parte 6 — Obter a Stream Key no YouTube

1. Acesse [studio.youtube.com](https://studio.youtube.com)
2. Clique em **Criar → Fazer live agora** ou acesse **Go Live** no painel
3. Em **Configurações do stream**, copie a **Chave de stream**
4. Opcionalmente, escolha o tipo de stream como **Persistente** para reutilizar sempre a mesma chave

---

## Parte 7 — Operação e manutenção

### Comandos úteis

| Ação | Comando |
|------|---------|
| Ver logs em tempo real | `docker logs -f restreamer` |
| Parar o container | `docker compose -f /opt/restreamer/docker-compose.yml stop` |
| Reiniciar | `docker compose -f /opt/restreamer/docker-compose.yml restart` |
| Atualizar a imagem | `docker compose -f /opt/restreamer/docker-compose.yml pull && docker compose up -d` |
| Ver uso de CPU/memória | `docker stats restreamer` |

### Monitorar temperatura do Pi

O re-encode de H.265 → H.264 é intensivo. Monitore a temperatura:

```bash
watch -n 2 vcgencmd measure_temp
```

> Acima de 80°C considere um dissipador ou cooler. O Pi 3B+ faz throttle de CPU a partir de ~82°C.

### Verificar uso de CPU

```bash
htop
```

ou

```bash
docker stats restreamer
```

---

## Parte 8 — Troubleshooting

### O container não sobe
```bash
docker logs restreamer
```
Verifique se as portas 8080, 1935 não estão em uso por outro serviço:
```bash
sudo ss -tulpn | grep -E '8080|1935'
```

### A câmera não conecta
Teste a URL RTSP fora do Restreamer:
```bash
sudo apt install -y ffmpeg
ffplay rtsp://usuario:senha@192.168.1.XX:554/stream
```
ou com VLC em outro computador da rede.

### Stream travando ou baixa qualidade
- Reduza a resolução para 854x480 nas configurações da fonte
- Mude o preset de `ultrafast` para `superfast` — pode melhorar a qualidade com pouco impacto na CPU
- Aumente o buffer RTSP: adicione `?tcp` ao final da URL RTSP ou force TCP nas configurações

### Temperatura muito alta
- Ative o modo de economia: reduza o framerate para 20fps nas configurações
- Use resolução 480p se 720p estiver saturando a CPU

---

## Resumo da arquitetura final

```
Câmera IP (H.265 RTSP)
        │
        ▼
  Raspberry Pi 3B+
  ┌─────────────────────────────────┐
  │  Docker Container: Restreamer   │
  │  ┌──────────────────────────┐  │
  │  │  FFmpeg                  │  │
  │  │  decode H.265 (CPU)      │  │
  │  │  encode H.264 (V4L2/CPU) │  │
  │  │  mux FLV/RTMP            │  │
  │  └──────────────────────────┘  │
  │  Interface Web :8080            │
  └─────────────────────────────────┘
        │                    │
        ▼                    ▼
  YouTube RTMP         Browser local
  (live stream)        (controle)
```

---

*Guia elaborado para datarhei Restreamer versão `rpi-latest` em Debian 12 Bookworm armhf.*
