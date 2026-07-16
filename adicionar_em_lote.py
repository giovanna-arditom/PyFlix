import json
import time
from datetime import date

from buscar_posteres import (
    IMAGE_BASE_URL,
    buscar_pagina_descoberta,
    mapear_generos,
    buscar_classificacao_tmdb,
    buscar_plataforma_tmdb,
    buscar_nota_imdb,
)

CAMINHO_CATALOGO = 'data/catalogo.json'

# Quantos titulos novos tentar adicionar em cada execucao do script.
QUANTIDADE_DESEJADA = 20

# Ha quantos anos, no minimo, o titulo precisa ter sido lancado.
# Ex: 2 = so traz titulos lancados ha 2 anos ou mais (evita coisa ainda em cartaz no cinema).
# Mude esse numero pra ajustar: 1 = mais recente, 5 = mais antigo.
IDADE_MINIMA_LANCAMENTO_ANOS = 2

# Classificacao usada quando a TMDB nao tem uma certificacao BR confiavel.
# 18 = mais restritiva, para nao arriscar mostrar algo inadequado antes da revisao manual.
CLASSIFICACAO_PADRAO_SEM_DADO = 18
PLATAFORMA_PADRAO_SEM_DADO = 'A definir'
NOTA_PADRAO_SEM_DADO = 0.0


def calcular_data_limite():
    hoje = date.today()
    try:
        data_limite = hoje.replace(year=hoje.year - IDADE_MINIMA_LANCAMENTO_ANOS)
    except ValueError:
        # cai em 29 de fevereiro num ano nao bissexto
        data_limite = hoje.replace(month=2, day=28, year=hoje.year - IDADE_MINIMA_LANCAMENTO_ANOS)
    return data_limite.strftime('%Y-%m-%d')


def carregar_catalogo():
    with open(CAMINHO_CATALOGO, 'r', encoding='utf-8') as arquivo:
        return json.load(arquivo)


def salvar_catalogo(catalogo):
    with open(CAMINHO_CATALOGO, 'w', encoding='utf-8') as arquivo:
        json.dump(catalogo, arquivo, ensure_ascii=False, indent=2)


def ja_existe_no_catalogo(titulo, titulos_existentes):
    """Verifica se o titulo (ou algo muito parecido) ja esta no catalogo,
    para nao duplicar entradas quando o script roda de novo."""
    return titulo.strip().lower() in titulos_existentes


def montar_item_do_resultado(resultado, pendencias):
    """Recebe um resultado bruto da TMDB (de /discover) e monta
    o item completo do catalogo, buscando os dados complementares."""
    tipo = 'filme' if resultado['media_type'] == 'movie' else 'serie'
    titulo_final = resultado.get('title') if tipo == 'filme' else resultado.get('name')
    # titulo original (normalmente em ingles) - usado so pra buscar a nota na OMDb,
    # que quase nunca reconhece o titulo traduzido pro portugues.
    titulo_original = resultado.get('original_title') if tipo == 'filme' else resultado.get('original_name')
    tmdb_id = resultado['id']

    sinopse = resultado.get('overview') or ''
    if not sinopse:
        pendencias.setdefault(titulo_final, []).append('sinopse vazia (não encontrada em pt-BR)')

    poster_path = resultado.get('poster_path')
    poster = IMAGE_BASE_URL + poster_path if poster_path else None
    if not poster:
        pendencias.setdefault(titulo_final, []).append('pôster não encontrado')

    generos = mapear_generos(resultado.get('genre_ids', []), tipo)
    if not generos:
        pendencias.setdefault(titulo_final, []).append('gênero não identificado')

    classificacao = buscar_classificacao_tmdb(tmdb_id, tipo)
    if classificacao is None:
        pendencias.setdefault(titulo_final, []).append(
            f'classificação etária não encontrada (usado {CLASSIFICACAO_PADRAO_SEM_DADO} como padrão de segurança)'
        )
        classificacao = CLASSIFICACAO_PADRAO_SEM_DADO

    onde = buscar_plataforma_tmdb(tmdb_id, tipo)
    if onde is None:
        pendencias.setdefault(titulo_final, []).append('plataforma de streaming não identificada')
        onde = PLATAFORMA_PADRAO_SEM_DADO

    nota = buscar_nota_imdb(titulo_original or titulo_final, tipo)
    if nota is None:
        pendencias.setdefault(titulo_final, []).append('nota do IMDb não encontrada')
        nota = NOTA_PADRAO_SEM_DADO

    return {
        'titulo': titulo_final,
        'tipo': tipo,
        'genero': generos,
        'classificacao': classificacao,
        'nota': nota,
        'sinopse': sinopse,
        'onde': onde,
        'poster': poster,
    }


def main():
    catalogo = carregar_catalogo()
    titulos_existentes = {item['titulo'].strip().lower() for item in catalogo}

    data_limite = calcular_data_limite()

    print('=== Adição automática ao catálogo do PyFlix ===')
    print(f'Buscando até {QUANTIDADE_DESEJADA} título(s) novo(s), lançados até {data_limite}...\n')

    pendencias = {}
    adicionados = 0
    pagina_filme = 1
    pagina_serie = 1
    tentativas_sem_resultado = 0

    while adicionados < QUANTIDADE_DESEJADA and tentativas_sem_resultado < 5:
        resultados = buscar_pagina_descoberta('filme', pagina_filme, data_limite)
        resultados += buscar_pagina_descoberta('serie', pagina_serie, data_limite)
        pagina_filme += 1
        pagina_serie += 1

        if not resultados:
            break

        encontrou_algo_novo_na_pagina = False

        for resultado in resultados:
            if adicionados >= QUANTIDADE_DESEJADA:
                break

            titulo_bruto = resultado.get('title') if resultado['media_type'] == 'movie' else resultado.get('name')
            if not titulo_bruto:
                continue

            # Verifica duplicidade ANTES de gastar chamadas de API buscando os detalhes.
            if ja_existe_no_catalogo(titulo_bruto, titulos_existentes):
                print(f'⏭️  "{titulo_bruto}" já está no catálogo. Pulando.')
                continue

            encontrou_algo_novo_na_pagina = True

            novo_item = montar_item_do_resultado(resultado, pendencias)

            # Segunda checagem: o titulo oficial pode diferir do titulo_bruto usado
            # na primeira verificacao (raro, mas acontece com acentuacao/pontuacao).
            if ja_existe_no_catalogo(novo_item['titulo'], titulos_existentes):
                print(f'⏭️  "{novo_item["titulo"]}" já está no catálogo (nome oficial). Pulando.')
                continue

            catalogo.append(novo_item)
            titulos_existentes.add(novo_item['titulo'].strip().lower())
            salvar_catalogo(catalogo)
            adicionados += 1
            print(f'✅ "{novo_item["titulo"]}" adicionado ({novo_item["tipo"]}).')
            time.sleep(0.3)

        tentativas_sem_resultado = 0 if encontrou_algo_novo_na_pagina else tentativas_sem_resultado + 1

    print(f'\nConcluído! {adicionados} título(s) novo(s) adicionado(s) ao catálogo.')

    if pendencias:
        print('\n⚠️  Itens que precisam de revisão manual no data/catalogo.json:')
        for titulo, avisos in pendencias.items():
            print(f'\n- {titulo}')
            for aviso in avisos:
                print(f'    • {aviso}')
    else:
        print('\nNenhuma pendência — todos os campos foram preenchidos automaticamente.')


if __name__ == '__main__':
    main()