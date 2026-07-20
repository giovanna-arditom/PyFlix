from flask import Flask, render_template, request, session
import json
import random
import os
from dotenv import load_dotenv
from buscar_posteres import buscar_poster, buscar_nota_imdb, buscar_titulo_oficial

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY')

SENHA_ADICIONAR = os.getenv('SENHA_ADICIONAR')

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
    'guerra e politica': 'Guerra e Política',
    'familia': 'Família',
    'historia': 'História',
    'misterio': 'Mistério',
    'terror': 'Terror',
    'reality show': 'Reality Show',
    'documentario': 'Documentário',
    'infantil': 'Infantil',
    'aventura': 'Aventura',
    'crime': 'Crime',
    'faroeste': 'Faroeste',
    'musical': 'Musical', 
    'thriller': 'Suspense', 
    'sci-fi & fantasy': 'Ficção Científica',
    'war & politics': 'Guerra e Política',
    'action & adventure': 'Ação'
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

@app.route('/adicionar', methods=['GET'])
def adicionar_formulario():
    catalogo = carregar_catalogo()
    generos = sorted(set(genero for item in catalogo for genero in item['genero']))
    plataformas = sorted(set(item['onde'] for item in catalogo))
    return render_template('adicionar.html', generos=generos, nomes_genero=NOMES_GENERO, plataformas=plataformas, erro=None, dados_form=None)


@app.route('/adicionar', methods=['POST'])
def adicionar_processar():
    catalogo = carregar_catalogo()
    generos = sorted(set(genero for item in catalogo for genero in item['genero']))
    plataformas = sorted(set(item['onde'] for item in catalogo))

    senha_digitada = request.form.get('senha', '')
    if senha_digitada != SENHA_ADICIONAR:
        return render_template('adicionar.html', generos=generos, nomes_genero=NOMES_GENERO,
                                plataformas=plataformas, erro='Senha incorreta. Tente novamente.',
                                dados_form=request.form)

    titulo = request.form.get('titulo', '').strip()
    tipo = request.form.get('tipo')
    confirmado = request.form.get('confirmado') == '1'

    if not confirmado:
        titulo_oficial = buscar_titulo_oficial(titulo, tipo)
        if titulo_oficial and titulo_oficial.strip().lower() != titulo.lower():
            dados_form = request.form.to_dict(flat=False)
            return render_template('confirmar_titulo.html', titulo_digitado=titulo,
                                    titulo_sugerido=titulo_oficial, dados_form=dados_form)

    classificacao = int(request.form.get('classificacao'))
    sinopse = request.form.get('sinopse', '').strip()
    onde = request.form.get('onde', '').strip()
    if onde == 'outro':
        onde = request.form.get('onde_outro', '').strip()

    generos_marcados = request.form.getlist('genero')
    generos_digitados = request.form.get('generos_novos', '')
    generos_novos = [g.strip().lower() for g in generos_digitados.split(',') if g.strip()]
    genero_final = sorted(set(generos_marcados + generos_novos))

    poster = buscar_poster(titulo, tipo)

    nota = request.form.get('nota', '')
    nota = nota.replace(',', '.')
    nota = float(nota) if nota else buscar_nota_imdb(titulo, tipo)


    novo_item = {
        'titulo': titulo,
        'tipo': tipo,
        'genero': genero_final,
        'classificacao': classificacao,
        'nota': nota,
        'sinopse': sinopse,
        'onde': onde,
        'poster': poster,
    }

    catalogo.append(novo_item)
    with open('data/catalogo.json', 'w', encoding='utf-8') as arquivo:
        json.dump(catalogo, arquivo, ensure_ascii=False, indent=2)

    return render_template('adicionar_sucesso.html', item=novo_item)


if __name__ == '__main__':
    app.run(debug=os.getenv('FLASK_DEBUG', 'False') == 'True')