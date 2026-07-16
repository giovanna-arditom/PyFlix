import os
import json
import time
import requests
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv('TMDB_API_KEY')
BASE_URL = 'https://api.themoviedb.org/3/search'
IMAGE_BASE_URL = 'https://image.tmdb.org/t/p/w500'


def buscar_poster(titulo, tipo):
    endpoint = 'movie' if tipo == 'filme' else 'tv'
    url = f'{BASE_URL}/{endpoint}'
    params = {
        'api_key': API_KEY,
        'query': titulo,
        'language': 'pt-BR'
    }

    resposta = requests.get(url, params=params)
    dados = resposta.json()

    resultados = dados.get('results', [])
    if resultados and resultados[0].get('poster_path'):
        return IMAGE_BASE_URL + resultados[0]['poster_path']
    return None


def buscar_titulo_oficial(titulo, tipo):
    endpoint = 'movie' if tipo == 'filme' else 'tv'
    url = f'{BASE_URL}/{endpoint}'
    params = {
        'api_key': API_KEY,
        'query': titulo,
        'language': 'pt-BR'
    }

    resposta = requests.get(url, params=params)
    dados = resposta.json()

    resultados = dados.get('results', [])
    if resultados:
        campo_titulo = 'title' if tipo == 'filme' else 'name'
        return resultados[0].get(campo_titulo)
    return None


def buscar_sinopse(titulo, tipo):
    endpoint = 'movie' if tipo == 'filme' else 'tv'
    url = f'{BASE_URL}/{endpoint}'
    params = {
        'api_key': API_KEY,
        'query': titulo,
        'language': 'pt-BR'
    }

    resposta = requests.get(url, params=params)
    dados = resposta.json()

    resultados = dados.get('results', [])
    if resultados and resultados[0].get('overview'):
        return resultados[0]['overview']
    return None


TMDB_BASE_URL = 'https://api.themoviedb.org/3'
_CACHE_GENEROS = {}


def buscar_multi(titulo):
    """Busca um titulo sem saber se e filme ou serie, usando /search/multi da TMDB.
    Retorna o primeiro resultado (filme ou serie) com os dados brutos da API, ou None."""
    url = f'{TMDB_BASE_URL}/search/multi'
    params = {
        'api_key': API_KEY,
        'query': titulo,
        'language': 'pt-BR'
    }

    resposta = requests.get(url, params=params)
    dados = resposta.json()

    for resultado in dados.get('results', []):
        if resultado.get('media_type') in ('movie', 'tv'):
            return resultado
    return None


def _normalizar_texto(texto):
    """Remove acentos e deixa em minusculo, no mesmo padrao ja usado no catalogo (ex: 'ficcao cientifica')."""
    import unicodedata
    sem_acento = unicodedata.normalize('NFKD', texto).encode('ASCII', 'ignore').decode('ASCII')
    return sem_acento.lower().strip()


def buscar_mapa_generos(tipo):
    """Busca e armazena em cache o mapa {id: nome} de generos da TMDB (filme ou serie)."""
    if tipo in _CACHE_GENEROS:
        return _CACHE_GENEROS[tipo]

    endpoint = 'movie' if tipo == 'filme' else 'tv'
    url = f'{TMDB_BASE_URL}/genre/{endpoint}/list'
    params = {'api_key': API_KEY, 'language': 'pt-BR'}

    resposta = requests.get(url, params=params)
    dados = resposta.json()

    mapa = {g['id']: g['name'] for g in dados.get('genres', [])}
    _CACHE_GENEROS[tipo] = mapa
    return mapa


def mapear_generos(genre_ids, tipo):
    """Converte os ids de genero da TMDB em generos no padrao do catalogo.
    Generos compostos (ex: 'Acao e aventura') sao separados em generos individuais."""
    mapa = buscar_mapa_generos(tipo)
    generos = set()
    for gid in genre_ids:
        nome = mapa.get(gid)
        if not nome:
            continue
        for parte in nome.split(' e '):
            generos.add(_normalizar_texto(parte))
    return sorted(generos)


def buscar_classificacao_tmdb(tmdb_id, tipo):
    """Busca a classificacao etaria oficial brasileira (ANCINE) na TMDB.
    Retorna um int (0, 10, 12, 14, 16 ou 18) ou None se nao encontrar/nao reconhecer."""
    valores_validos = {'L': 0, '10': 10, '12': 12, '14': 14, '16': 16, '18': 18}

    if tipo == 'filme':
        url = f'{TMDB_BASE_URL}/movie/{tmdb_id}/release_dates'
        resposta = requests.get(url, params={'api_key': API_KEY})
        dados = resposta.json()
        for pais in dados.get('results', []):
            if pais.get('iso_3166_1') == 'BR':
                for release in pais.get('release_dates', []):
                    cert = release.get('certification', '').strip()
                    if cert in valores_validos:
                        return valores_validos[cert]
    else:
        url = f'{TMDB_BASE_URL}/tv/{tmdb_id}/content_ratings'
        resposta = requests.get(url, params={'api_key': API_KEY})
        dados = resposta.json()
        for pais in dados.get('results', []):
            if pais.get('iso_3166_1') == 'BR':
                cert = pais.get('rating', '').strip()
                if cert in valores_validos:
                    return valores_validos[cert]
    return None


MAPA_PLATAFORMAS = {
    'netflix': 'Netflix',
    'amazon prime video': 'Prime Video',
    'prime video': 'Prime Video',
    'max': 'HBO Max',
    'hbo max': 'HBO Max',
    'disney plus': 'Disney +',
    'disney+': 'Disney +',
    'globoplay': 'Globoplay',
    'apple tv plus': 'Apple TV+',
    'paramount plus': 'Paramount+',
}


def buscar_plataforma_tmdb(tmdb_id, tipo):
    """Busca em que plataforma de streaming (assinatura) o titulo esta disponivel no Brasil.
    Retorna o nome no padrao usado no catalogo, ou None se nao achar nenhuma conhecida."""
    endpoint = 'movie' if tipo == 'filme' else 'tv'
    url = f'{TMDB_BASE_URL}/{endpoint}/{tmdb_id}/watch/providers'
    resposta = requests.get(url, params={'api_key': API_KEY})
    dados = resposta.json()

    provedores = dados.get('results', {}).get('BR', {}).get('flatrate', [])
    for provedor in provedores:
        nome_normalizado = _normalizar_texto(provedor.get('provider_name', ''))
        if nome_normalizado in MAPA_PLATAFORMAS:
            return MAPA_PLATAFORMAS[nome_normalizado]
    return None


def buscar_pagina_descoberta(tipo, pagina, data_limite):
    """Busca uma pagina de titulos populares de um tipo (filme ou serie), usando /discover,
    excluindo qualquer coisa lancada depois de 'data_limite' (formato 'AAAA-MM-DD').
    Isso evita trazer lancamentos recentes/ainda em cartaz no cinema."""
    endpoint = 'movie' if tipo == 'filme' else 'tv'
    campo_data = 'primary_release_date' if tipo == 'filme' else 'first_air_date'

    url = f'{TMDB_BASE_URL}/discover/{endpoint}'
    params = {
        'api_key': API_KEY,
        'language': 'pt-BR',
        'page': pagina,
        'sort_by': 'popularity.desc',
        'vote_count.gte': 50,
        f'{campo_data}.lte': data_limite,
    }

    resposta = requests.get(url, params=params)
    dados = resposta.json()

    resultados = dados.get('results', [])
    # /discover nao devolve 'media_type', entao marcamos manualmente
    # (montar_item_do_resultado espera esse campo, igual /search/multi e /trending).
    for r in resultados:
        r['media_type'] = endpoint
    return resultados


OMDB_API_KEY = os.getenv('OMDB_API_KEY')


def buscar_nota_imdb(titulo, tipo):
    """Busca a nota do IMDb na OMDb. IMPORTANTE: a OMDb indexa pelo titulo ORIGINAL
    (normalmente em ingles), entao passar um titulo traduzido pra pt-BR quase sempre
    retorna vazio. Quem chama essa funcao com um resultado da TMDB deve passar
    original_title/original_name, nao title/name."""
    tipo_omdb = 'movie' if tipo == 'filme' else 'series'
    params = {
        'apikey': OMDB_API_KEY,
        't': titulo,
        'type': tipo_omdb
    }

    resposta = requests.get('https://www.omdbapi.com/', params=params)
    dados = resposta.json()

    nota = dados.get('imdbRating')
    if nota and nota != 'N/A':
        return float(nota)
    return None


def main():
    with open('data/catalogo.json', 'r', encoding='utf-8') as arquivo:
        catalogo = json.load(arquivo)

    for item in catalogo:
        if item.get('poster'):
            print(f"{item['titulo']}: ja tinha poster, pulando")
            continue

        poster = buscar_poster(item['titulo'], item['tipo'])
        item['poster'] = poster
        status = 'OK' if poster else 'NAO ENCONTRADO'
        print(f"{item['titulo']}: {status}")
        time.sleep(0.3)

    with open('data/catalogo.json', 'w', encoding='utf-8') as arquivo:
        json.dump(catalogo, arquivo, ensure_ascii=False, indent=2)

    print('\nConcluido! catalogo.json atualizado com os posteres.')


if __name__ == '__main__':
    main()