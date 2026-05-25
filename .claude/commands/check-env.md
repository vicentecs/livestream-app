# Verificar variáveis de ambiente

Verifica se o `.env` está completo e bem formado antes de subir a stack.

## Instruções

1. Leia `.env.example` para ver todas as variáveis obrigatórias
2. Verifique se o `.env` existe: `ls -la .env`
3. Compare as chaves presentes no `.env` com as do `.env.example`
4. Para cada variável faltando ou vazia, informe claramente
5. **Nunca exiba os valores** — apenas confirme presença/ausência

## Variáveis obrigatórias

| Variável | Onde obter |
|---|---|
| `GOOGLE_CLIENT_ID` | Google Cloud Console → Credenciais |
| `GOOGLE_CLIENT_SECRET` | Google Cloud Console → Credenciais |
| `APP_SECRET_KEY` | Gerar com: `python3 -c "import secrets; print(secrets.token_hex(32))"` |
| `APP_PUBLIC_URL` | URL do Cloudflare Tunnel (ex: `https://live.seudominio.com`) |
| `RESTREAMER_URL` | Sempre `http://restreamer:8080` |
| `RESTREAMER_USER` | Definido na primeira execução do Restreamer |
| `RESTREAMER_PASS` | Definido na primeira execução do Restreamer |
| `RTSP_URL` | URL da câmera IP |
| `CLOUDFLARE_TUNNEL_TOKEN` | Cloudflare Zero Trust → Tunnels |

## Output esperado

Informe o status de cada variável e, ao final, se o `.env` está pronto para uso.
Se tiver variáveis faltando, mostre o comando para gerá-las ou onde obtê-las.
