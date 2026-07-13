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