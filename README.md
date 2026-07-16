# 🎲 PyFlix

Site de recomendação de filmes e séries para aqueles dias em que você não sabe o que assistir. Você aplica filtros (idade, nota mínima, gênero, plataforma) e o PyFlix sorteia uma sugestão do catálogo.

🔗 **Site publicado:** [pyflix.onrender.com](https://pyflix.onrender.com)
📦 **Repositório:** [github.com/giovanna-arditom/PyFlix](https://github.com/giovanna-arditom/PyFlix)

## Funcionalidades

- **Recomendação filtrada** por classificação etária máxima, nota mínima do IMDb, tipo de conteúdo (filme/série), gêneros que você quer ou não quer ver, e plataforma de streaming.
- **Sorteio com "próxima sugestão"**: se a recomendação não agradar, dá pra pedir outra sem refazer os filtros.
- **Adicionar novo conteúdo** ao catálogo por um formulário protegido por senha, com:
  - confirmação automática do título oficial via OMDb (evita duplicar títulos com nomes diferentes);
  - busca automática de pôster (TMDb) e nota do IMDb (OMDb) — a nota também pode ser digitada manualmente, já que a OMDb nem sempre encontra títulos em português.

## Stack

- **Backend:** Python + Flask
- **Frontend:** HTML + CSS (templates Jinja2, sem framework JS)
- **Dados:** arquivo `data/catalogo.json` (sem banco de dados)
- **APIs externas:** TMDb (pôsteres) e OMDb (nota IMDb e confirmação de título)
- **Deploy:** [Render](https://render.com) (free tier)
- **Servidor de produção:** Gunicorn

## Estrutura do projeto

```
PyFlix/
├── app.py                  # rotas e lógica principal
├── buscar_posteres.py       # integrações com TMDb e OMDb
├── requirements.txt
├── data/
│   └── catalogo.json        # catálogo de filmes/séries
├── static/
│   ├── style.css
│   └── images/
│       └── logo.png
└── templates/
    ├── index.html            # página inicial com filtros
    ├── resultado.html         # recomendação sorteada
    ├── adicionar.html         # formulário de adicionar conteúdo
    ├── confirmar_titulo.html  # confirmação de título via OMDb
    └── adicionar_sucesso.html # confirmação de item adicionado
```

## Rodando localmente

1. Clone o repositório e entre na pasta:
   ```bash
   git clone https://github.com/giovanna-arditom/PyFlix.git
   cd PyFlix
   ```

2. Crie e ative um ambiente virtual (opcional, mas recomendado):
   ```bash
   python -m venv venv
   venv\Scripts\activate      # Windows
   source venv/bin/activate   # Linux/Mac
   ```

3. Instale as dependências:
   ```bash
   pip install -r requirements.txt
   ```

4. Crie um arquivo `.env` na raiz do projeto com as variáveis:
   ```
   TMDB_API_KEY=sua_chave_aqui
   OMDB_API_KEY=sua_chave_aqui
   SENHA_ADICIONAR=sua_senha_aqui
   FLASK_SECRET_KEY=uma_chave_secreta_qualquer
   FLASK_DEBUG=True
   ```

5. Rode o app:
   ```bash
   python app.py
   ```
   O site sobe em `http://127.0.0.1:5000`.

## Deploy (Render)

O deploy é automático: qualquer push na branch `main` do GitHub dispara um novo deploy no Render.

- **Build Command:** `pip install -r requirements.txt`
- **Start Command:** `gunicorn app:app`
- **Variáveis de ambiente** (configuradas no painel do Render): `TMDB_API_KEY`, `OMDB_API_KEY`, `SENHA_ADICIONAR`, `FLASK_SECRET_KEY`, `FLASK_DEBUG=False`

> ⚠️ **Limitação conhecida:** no free tier do Render, o filesystem é efêmero. Isso significa que conteúdo adicionado pelo formulário `/adicionar` funciona normalmente enquanto o serviço está no ar, mas se perde quando o serviço reinicia, redeploya ou "dorme" por inatividade. Resolver isso (ex: migrar para um banco de dados ou storage externo) fica para uma próxima atualização.

## Autora

Giovanna Ardito M.
