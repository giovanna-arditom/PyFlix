from flask import Flask, render_template, request, session
import json
import random

app = Flask(__name__)
app.secret_key = 'troque-isso-por-uma-frase-aleatoria-so-sua'

NOMES_GENERO = {
    'acao': 'Ação',
    'animacao': 'Animação',
    'comedia': 'Comédia',
    'drama': 'Drama',
    'fantasia': 'Fantasia',
    'ficcao cientifica': 'Ficção Científica',
    'musical': 'Musical',
    'romance': 'Romance',
    'sitcom': 'Sitcom',
    'suspense': 'Suspense',
}

def carregar_catalogo():
    with open('data/catalogo.json', 'r', encoding='utf-8') as arquivo:
        return json.load(arquivo)

@app.route('/')
def home():
    catalogo = carregar_catalogo()
    generos = sorted(set(genero for item in catalogo for genero in item['genero']))
    plataformas = sorted(set(item['onde'] for item in catalogo))
    return render_template('index.html', generos=generos, nomes_genero=NOMES_GENERO, plataformas=plataformas)

@app.route('/recomendar')
def recomendar():
    catalogo = carregar_catalogo()

    idade_max = int(request.args.get('idade'))
    nota_min = request.args.get('nota_min')
    tipo = request.args.get('tipo')
    generos_quero = request.args.getlist('genero_quero')
    generos_nao_quero = request.args.getlist('genero_nao_quero')
    plataformas_escolhidas = request.args.getlist('onde')

    nota_min = float(nota_min) if nota_min else None

    recomendados = []
    for item in catalogo:
        if item['classificacao'] > idade_max:
            continue
        if nota_min and item['nota'] < nota_min:
            continue
        if tipo and tipo != 'qualquer' and item['tipo'] != tipo:
            continue
        if generos_quero and not any(g in item['genero'] for g in generos_quero):
            continue
        if generos_nao_quero and any(g in item['genero'] for g in generos_nao_quero):
            continue
        if plataformas_escolhidas and item['onde'] not in plataformas_escolhidas:
            continue
        recomendados.append(item)

    random.shuffle(recomendados)

    if not recomendados:
        return render_template('resultado.html', item=None, acabou=False)

    session['recomendados'] = [item['titulo'] for item in recomendados]
    session['posicao'] = 0

    item_atual = recomendados[0]
    contador = f"1 de {len(recomendados)}"
    return render_template('resultado.html', item=item_atual, contador=contador, acabou=False)


@app.route('/proxima')
def proxima():
    catalogo = carregar_catalogo()
    ids = session.get('recomendados', [])
    posicao = session.get('posicao', 0) + 1

    if posicao >= len(ids):
        return render_template('resultado.html', item=None, acabou=True)

    session['posicao'] = posicao
    titulo_atual = ids[posicao]
    item_atual = next((i for i in catalogo if i['titulo'] == titulo_atual), None)
    contador = f"{posicao + 1} de {len(ids)}"
    return render_template('resultado.html', item=item_atual, contador=contador, acabou=False)

if __name__ == '__main__':
    app.run(debug=True)