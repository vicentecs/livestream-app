# Setup Google Cloud Console

[← Voltar ao README](../README.md)

Configuração única — feita uma vez pelo administrador do sistema.

---

## 1. Criar o projeto

1. Acesse [console.cloud.google.com](https://console.cloud.google.com)
2. Clique em **Selecionar projeto → Novo projeto**
3. Nome: `livestream-orchestrator` (ou outro de sua escolha)
4. Clique em **Criar**

---

## 2. Habilitar a YouTube Data API v3

1. No menu lateral: **APIs e Serviços → Biblioteca**
2. Busque: `YouTube Data API v3`
3. Clique na API → **Ativar**

---

## 3. Configurar a tela de consentimento OAuth

1. Menu lateral: **APIs e Serviços → Tela de consentimento OAuth**
2. Tipo de usuário: **Externo** → Criar
3. Preencha:
   - **Nome do app:** Livestream Orchestrator
   - **E-mail de suporte:** seu e-mail
   - **E-mail do desenvolvedor:** seu e-mail
4. Clique em **Salvar e continuar**

### Escopos (tela seguinte)

1. Clique em **Adicionar ou remover escopos**
2. Busque e adicione:
   - `https://www.googleapis.com/auth/youtube` — gerenciar conta YouTube
3. Clique em **Atualizar → Salvar e continuar**

### Usuários de teste (tela seguinte)

1. Clique em **Adicionar usuários**
2. Adicione o e-mail Google de cada pessoa que vai usar o sistema
3. Clique em **Salvar e continuar**

> **Importante:** só e-mails cadastrados aqui conseguirão fazer login enquanto o app estiver em modo de teste. O status permanece em **Em teste** — não clique em "Publicar app".

---

## 4. Criar as credenciais OAuth

1. Menu lateral: **APIs e Serviços → Credenciais**
2. Clique em **Criar credenciais → ID do cliente OAuth 2.0**
3. Tipo de aplicativo: **Aplicativo da Web**
4. Nome: `Livestream App`
5. Em **URIs de redirecionamento autorizados**, adicione:
   ```
   https://live.seudominio.com/auth/callback
   ```
   Se quiser testar localmente também:
   ```
   http://localhost:3000/auth/callback
   ```
6. Clique em **Criar**
7. Anote o **Client ID** e o **Client Secret** — serão usados no `.env`

---

## 5. Preencher o .env

```env
GOOGLE_CLIENT_ID=seu-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=seu-client-secret
```

---

## Adicionar novos usuários

Quando um novo usuário precisar de acesso:

1. Acesse [console.cloud.google.com](https://console.cloud.google.com)
2. Selecione o projeto `livestream-orchestrator`
3. **APIs e Serviços → Tela de consentimento OAuth**
4. Seção **Usuários de teste → Adicionar usuários**
5. Adicione o e-mail Google do novo usuário

O usuário já poderá fazer login imediatamente — sem necessidade de reiniciar o sistema.

---

## Limite e considerações

- Máximo de **100 usuários de teste** no modo não verificado
- O app em modo de teste expira após **6 meses de inatividade** por usuário — o refresh token é revogado e o usuário precisa fazer login novamente
- O aviso "App não verificado" aparece no login — o usuário deve clicar em **Avançado → Acessar (nome do app)** para continuar

---

_Última revisão: 2026-05-25._

