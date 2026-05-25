# Troubleshooting

[← Voltar ao README](../README.md)

Soluções para problemas frequentes em produção.

## Sumário

- [App não sobe / container em loop](#app-não-sobe--container-em-loop)
- [Login Google falha — "redirect_uri_mismatch"](#login-google-falha--redirect_uri_mismatch)
- [Login Google falha — "Access blocked: app not verified"](#login-google-falha--access-blocked-app-not-verified)
- [Refresh token inválido / usuário precisa logar sempre](#refresh-token-inválido--usuário-precisa-logar-sempre)
- [Live inicia mas não aparece no YouTube](#live-inicia-mas-não-aparece-no-youtube)
- [Câmera RTSP não conecta](#câmera-rtsp-não-conecta)
- [Alta temperatura no Pi / throttle](#alta-temperatura-no-pi--throttle)
- [Stream trava como "ocupado" sem live ativa](#stream-trava-como-ocupado-sem-live-ativa)
- [Tunnel Cloudflare não conecta](#tunnel-cloudflare-não-conecta)
- [Atualizar para nova versão](#atualizar-para-nova-versão)

> Se nenhum cenário cobrir seu problema, abra uma issue — ver [CONTRIBUTING.md#reportar-bugs](../CONTRIBUTING.md#reportar-bugs).

---

## App não sobe / container em loop

```bash
docker compose logs app
```

Causas comuns:
- `.env` incompleto — verificar se todas as variáveis obrigatórias estão preenchidas
- Porta 3000 já em uso: `sudo ss -tulpn | grep 3000`
- Restreamer ainda inicializando — aguardar 20s e tentar novamente

---

## Login Google falha — "redirect_uri_mismatch"

O URI de callback no Google Cloud Console não bate com `APP_PUBLIC_URL`.

**Verificar:**
1. `APP_PUBLIC_URL` no `.env` — deve ser exatamente `https://live.seudominio.com` (sem barra no final)
2. No Google Cloud Console, o URI cadastrado deve ser `https://live.seudominio.com/auth/callback`
3. Os dois devem ser idênticos — incluindo `https` vs `http`

---

## Login Google falha — "Access blocked: app not verified"

O usuário não está na lista de testadores.

**Solução:** Adicionar o e-mail Google do usuário em **Google Cloud Console → Tela de consentimento OAuth → Usuários de teste**.

---

## Refresh token inválido / usuário precisa logar sempre

O refresh token foi revogado. Causas:
- Usuário removeu o acesso em myaccount.google.com
- App ficou em modo de teste sem uso por 6 meses
- Senha da conta Google foi alterada

**Solução:** Usuário faz logout e login novamente. Na tela do Google, deve aparecer a tela de consentimento completa novamente para gerar novo refresh token.

Se a tela de consentimento não aparecer (Google já autorizou):

```
https://accounts.google.com/o/oauth2/auth?prompt=consent&...
```

Adicionar `prompt=consent` ao URL de autorização força a tela — já está implementado em `auth.py`.

---

## Live inicia mas não aparece no YouTube

Sequência de verificação:

1. **Restreamer está enviando vídeo?**
   ```bash
   docker compose logs restreamer | tail -50
   ```
   Procurar por `frame=` no output do FFmpeg — indica que está processando.

2. **Stream key está correta?**
   Verificar no YouTube Studio se a stream key do broadcast criado bate com a que foi enviada ao Restreamer.

3. **YouTube recebeu o vídeo?**
   No YouTube Studio → Go Live → verificar se o indicador de stream está verde.

4. **Broadcast foi para o estado "live"?**
   O sistema faz a transição automaticamente após detectar `streamStatus=active`. Se travar em "testing", verificar logs da app:
   ```bash
   docker compose logs app | grep transition
   ```

---

## Câmera RTSP não conecta

Testar a URL RTSP diretamente no Pi:

```bash
docker compose exec app bash
# dentro do container:
apt install -y ffmpeg
ffprobe -v quiet -print_format json -show_streams "rtsp://usuario:senha@IP:554/stream"
```

Se o ffprobe retornar informações do stream, confirmar que o codec de vídeo é **H.264** (`codec_name: h264`). Se não:
- Verificar configuração da câmera — garantir que o stream principal está configurado para H.264 (não H.265/HEVC)
- Verificar se a câmera está na mesma rede do Pi
- Testar caminhos alternativos como `/live`, `/stream`, `/stream1`, `/ch0`
- Verificar credenciais da câmera
- Algumas câmeras exigem `rtsp_transport tcp` — adicionar `?tcp` ao final da URL RTSP

**Câmera retorna H.264 mas stream trava ou corrompe no YouTube:**
- Verificar perfil e nível do H.264: o YouTube aceita Baseline, Main e High até nível 4.2
- Se a câmera usar perfil incompatível, será necessário re-encode pontual — abrir issue no repositório para avaliar

**Verificar codec diretamente:**
```bash
ffprobe -v error -select_streams v:0 -show_entries stream=codec_name,profile,level \
  -of default=noprint_wrappers=1 "rtsp://usuario:senha@IP:554/stream"
```
Saída esperada: `codec_name=h264`, perfil Main ou High, nível ≤ 42.

---

## Alta temperatura no Pi / throttle

Com pipeline de remux H.264 (sem re-encode), o uso de CPU fica em ~5–15% e a temperatura raramente passa de 60°C em condições normais. Se mesmo assim ocorrer throttle:

```bash
watch -n 2 vcgencmd measure_temp
```

Se acima de 80°C, investigar causa — o remux puro não deveria gerar essa carga:
- Verificar se o Restreamer está fazendo re-encode inesperadamente (checar logs: deve aparecer `-c:v copy`, não `libx264`)
- Instalar dissipador se o Pi estiver em ambiente quente
- Verificar outros processos consumindo CPU: `htop`

Verificar se o throttle está ativo:
```bash
vcgencmd get_throttled
# 0x0 = sem throttle
# qualquer outro valor = throttle ativo
```

---

## Stream trava como "ocupado" sem live ativa

O lock ficou preso — geralmente porque o container foi reiniciado durante uma live.

O lock é em memória, então reiniciar a app libera automaticamente:

```bash
docker compose restart app
```

---

## Tunnel Cloudflare não conecta

```bash
docker compose logs cloudflared
```

Causas comuns:
- `CLOUDFLARE_TUNNEL_TOKEN` inválido ou expirado — regenerar no Cloudflare Zero Trust
- Container sem acesso à internet — verificar DNS do Pi:
  ```bash
  ping 1.1.1.1
  ```
- Conflito de porta — verificar se outro serviço está usando a porta 3000

---

## Atualizar para nova versão

```bash
cd /opt/livestream
docker compose pull
docker compose up -d
docker compose logs -f app
```

Para verificar qual versão está rodando:

```bash
docker inspect livestream-app | grep Image
```

---

_Última revisão: 2026-05-25._

