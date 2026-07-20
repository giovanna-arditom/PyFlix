import json
import os
import random
import time
from datetime import date

from buscar_posteres import (
    IMAGE_BASE_URL,
    buscar_pagina_descoberta,
    mapear_generos,
    buscar_ids_generos,
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

# Quais generos buscar: agora e perguntado no terminal toda vez que o script
# roda (funcao perguntar_generos_desejados(), la embaixo) - basta apertar Enter
# pra buscar qualquer genero, sem filtro, ou digitar o(s) genero(s) desejado(s).
#
# Alguns nomes validos (filme e/ou serie): acao, aventura, animacao, comedia,
# crime, documentario, drama, familia, fantasia, historia, terror, misterio,
# musica, romance, ficcao cientifica, cinema tv, thriller, guerra, faroeste,
# kids, novela, reality, talk. Pode digitar com ou sem acento/maiusculas -
# o script normaliza sozinho.

# Faixa de paginas do /discover que o script sorteia a cada execucao, em vez de
# sempre andar 1, 2, 3... (por isso vinha sempre os mesmos titulos antes).
# Pagina 1 = mais populares; paginas mais altas trazem coisa progressivamente
# menos conhecida (o filtro de vote_count/vote_average em buscar_posteres.py
# ja segura o pior disso, mas nao exagere nesse numero pra nao cair em titulo obscuro).
PAGINA_MINIMA = 1
PAGINA_MAXIMA = 40

# Quantas rodadas (par de paginas filme+serie) seguidas SEM adicionar nenhum
# titulo novo o script tolera antes de desistir. Precisa ser generoso porque
# agora muitos titulos sao ignorados (sem sinopse/plataforma) sem contar como
# progresso - isso NAO deveria fazer o script desistir cedo demais.
LIMITE_TENTATIVAS_SEM_PROGRESSO = 30

# Classificacao usada quando a TMDB nao tem uma certificacao BR confiavel.
# 18 = mais restritiva, para nao arriscar mostrar algo inadequado antes da revisao manual.
CLASSIFICACAO_PADRAO_SEM_DADO = 18


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


def perguntar_generos_desejados():
    """Pergunta no terminal se a pessoa quer filtrar por genero especifico.
    Enter em branco = sem filtro (qualquer genero, comportamento antigo).
    Aceita um ou varios generos separados por virgula (ex: 'documentario, drama')."""
    resposta = input(
        'Buscar algum gênero específico? (Enter para qualquer gênero, '
        'ou digite um ou mais separados por vírgula, ex: documentario, drama): '
    ).strip()

    if not resposta:
        return []

    return [genero.strip() for genero in resposta.split(',') if genero.strip()]


def gerar_ordem_paginas():
    """Gera a lista de paginas (1 a PAGINA_MAXIMA) em ordem embaralhada.
    Usamos .pop() nela, entao cada pagina so e usada uma vez por 'rodada'."""
    paginas = list(range(PAGINA_MINIMA, PAGINA_MAXIMA + 1))
    random.shuffle(paginas)
    return paginas


def montar_item_do_resultado(resultado, pendencias, ignorados):
    """Recebe um resultado bruto da TMDB (de /discover) e monta o item completo
    do catalogo, buscando os dados complementares.

    Retorna None (e registra o motivo em 'ignorados') se faltar sinopse em pt-BR
    ou se nao encontrar em qual plataforma de streaming o titulo esta disponivel -
    nesses casos o titulo e pulado, nao entra no catalogo com valor padrao."""
    tipo = 'filme' if resultado['media_type'] == 'movie' else 'serie'
    titulo_final = resultado.get('title') if tipo == 'filme' else resultado.get('name')
    # titulo original (normalmente em ingles) - usado so pra buscar a nota na OMDb,
    # que quase nunca reconhece o titulo traduzido pro portugues.
    titulo_original = resultado.get('original_title') if tipo == 'filme' else resultado.get('original_name')
    tmdb_id = resultado['id']

    # Sinopse: se nao tem em pt-BR, pula direto (nem vale gastar as outras chamadas de API).
    sinopse = resultado.get('overview') or ''
    if not sinopse:
        ignorados.setdefault(titulo_final, []).append('sem sinopse em pt-BR')
        return None

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

    # Plataforma: se nao encontrar onde assistir, pula (antes de gastar a chamada da OMDb pra nota).
    onde = buscar_plataforma_tmdb(tmdb_id, tipo)
    if onde is None:
        ignorados.setdefault(titulo_final, []).append('plataforma de streaming não identificada')
        return None

    nota = buscar_nota_imdb(titulo_original or titulo_final, tipo)
    if nota is None:
        pendencias.setdefault(titulo_final, []).append('nota do IMDb não encontrada')
        nota = 0.0

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

    generos_desejados = perguntar_generos_desejados()
    generos_ids_filme = buscar_ids_generos(generos_desejados, 'filme')
    generos_ids_serie = buscar_ids_generos(generos_desejados, 'serie')

    if generos_desejados and not generos_ids_filme and not generos_ids_serie:
        print(f'⚠️  Nenhum gênero conhecido bateu com "{", ".join(generos_desejados)}". '
              'Buscando sem filtro de gênero.\n')
        generos_desejados = []

    print('=== Adição automática ao catálogo do PyFlix ===')
    print(f'📄 Arquivo usado: {os.path.abspath(CAMINHO_CATALOGO)}')
    print(f'📄 Itens no catálogo antes de rodar: {len(catalogo)}')
    if generos_desejados:
        print(f'🎯 Filtrando por gênero(s): {", ".join(generos_desejados)}')
    print(f'Buscando até {QUANTIDADE_DESEJADA} título(s) novo(s), lançados até {data_limite}...\n')

    pendencias = {}
    ignorados = {}
    adicionados = 0
    tentativas_sem_resultado = 0

    paginas_filme = gerar_ordem_paginas()
    paginas_serie = gerar_ordem_paginas()

    while adicionados < QUANTIDADE_DESEJADA and tentativas_sem_resultado < LIMITE_TENTATIVAS_SEM_PROGRESSO:
        if not paginas_filme:
            paginas_filme = gerar_ordem_paginas()
        if not paginas_serie:
            paginas_serie = gerar_ordem_paginas()

        pagina_filme = paginas_filme.pop()
        pagina_serie = paginas_serie.pop()

        resultados = buscar_pagina_descoberta('filme', pagina_filme, data_limite, generos_ids_filme)
        resultados += buscar_pagina_descoberta('serie', pagina_serie, data_limite, generos_ids_serie)
        random.shuffle(resultados)

        if not resultados:
            tentativas_sem_resultado += 1
            continue

        adicionou_algo_nesta_rodada = False

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

            novo_item = montar_item_do_resultado(resultado, pendencias, ignorados)

            if novo_item is None:
                motivo = ignorados.get(titulo_bruto, ['dado essencial ausente'])[-1]
                print(f'🚫 "{titulo_bruto}" ignorado: {motivo}.')
                continue

            # Segunda checagem: o titulo oficial pode diferir do titulo_bruto usado
            # na primeira verificacao (raro, mas acontece com acentuacao/pontuacao).
            if ja_existe_no_catalogo(novo_item['titulo'], titulos_existentes):
                print(f'⏭️  "{novo_item["titulo"]}" já está no catálogo (nome oficial). Pulando.')
                continue

            catalogo.append(novo_item)
            titulos_existentes.add(novo_item['titulo'].strip().lower())
            salvar_catalogo(catalogo)
            adicionados += 1
            adicionou_algo_nesta_rodada = True
            print(f'✅ "{novo_item["titulo"]}" adicionado ({novo_item["tipo"]}).')
            time.sleep(0.3)

        tentativas_sem_resultado = 0 if adicionou_algo_nesta_rodada else tentativas_sem_resultado + 1

    print(f'\nConcluído! {adicionados} título(s) novo(s) adicionado(s) ao catálogo.')

    # Titulos ignorados podem ter deixado avisos em 'pendencias' antes de serem
    # descartados (ex: aviso de classificacao registrado antes de descobrirmos
    # que faltava a plataforma). Remove esses casos pra nao aparecerem como se
    # precisassem de revisao manual, ja que nem foram adicionados ao catalogo.
    for titulo_ignorado in ignorados:
        pendencias.pop(titulo_ignorado, None)

    # Confere lendo o arquivo direto do disco (nao usa a variavel 'catalogo' em
    # memoria), pra garantir que o que foi salvo e realmente o que esta la.
    catalogo_no_disco = carregar_catalogo()
    print(f'📄 Itens no catálogo depois de rodar (relido do disco): {len(catalogo_no_disco)}')
    titulos_no_disco = {item['titulo'].strip().lower() for item in catalogo_no_disco}
    if adicionados > 0 and not (titulos_existentes <= titulos_no_disco):
        print('⚠️  ATENÇÃO: o script disse que adicionou títulos, mas eles NÃO estão no arquivo '
              'relido do disco. Verifique se não existe outro catalogo.json sendo usado por '
              'outra parte do projeto (ex: dentro de public/, build/, ou outro repositório), '
              'ou se o caminho acima corresponde ao arquivo que você está abrindo.')

    if ignorados:
        print(f'\n🚫 {len(ignorados)} título(s) ignorado(s) por falta de sinopse ou plataforma de streaming:')
        for titulo, avisos in ignorados.items():
            print(f'  - {titulo}: {", ".join(avisos)}')

    if pendencias:
        print('\n⚠️  Itens adicionados que precisam de revisão manual no data/catalogo.json:')
        for titulo, avisos in pendencias.items():
            print(f'\n- {titulo}')
            for aviso in avisos:
                print(f'    • {aviso}')
    else:
        print('\nNenhuma pendência — todos os campos foram preenchidos automaticamente.')


if __name__ == '__main__':
    main()