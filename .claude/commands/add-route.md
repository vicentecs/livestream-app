# Adicionar nova rota FastAPI

Crie uma nova rota em `app/main.py` seguindo estas convenções do projeto:

## Instruções

1. Leia `app/main.py` para entender as rotas existentes
2. Leia `app/models.py` para os tipos disponíveis
3. Leia `app/middleware.py` para entender os guards de autenticação

## Convenções obrigatórias

- Toda rota deve ser `async def`
- Rotas protegidas usam `current_user: User = Depends(get_current_user)`
- Rotas que acessam YouTube API chamam `auth.ensure_valid_token(user)` antes
- Respostas de erro usam o formato padronizado de `docs/api.md`
- Type hints obrigatórios em todos os parâmetros e retornos
- Usar `httpx.AsyncClient` para chamadas HTTP externas (não `requests`)

## Template

```python
@app.post("/novo-endpoint", response_model=RespostaModel)
async def novo_endpoint(
    body: BodyModel,
    current_user: User = Depends(get_current_user)
) -> RespostaModel:
    """Descrição clara do que a rota faz."""
    # implementação
```

## Após criar a rota

- Adicionar documentação em `docs/api.md`
- Verificar se precisa de entrada no `CLAUDE.md` (seção "Não fazer")
