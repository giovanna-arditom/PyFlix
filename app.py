from flask import Flask, render_template, request
import json
import random

app = Flask(__name__)

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
    return render_template('index.html', generos=generos, nomes_genero=NOMES_GENERO)

@app.route('/recomendar')
def recomendar():
    catalogo = carregar_catalogo()

    idade_max = int(request.args.get('idade'))
    nota_min = request.args.get('nota_min')
    tipo = request.args.get('tipo')
    generos_quero = request.args.getlist('genero_quero')
    generos_nao_quero = request.args.getlist('genero_nao_quero')

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
        recomendados.append(item)

    escolhido = random.choice(recomendados) if recomendados else None

    return render_template('resultado.html', item=escolhido, filtros=request.query_string.decode())

if __name__ == '__main__':
    app.run(debug=True)