import pandas as pd
import spacy
from pymongo import MongoClient
import os
import spacy
from textblob import TextBlob
from collections import defaultdict
from datetime import datetime
from textstat import textstat

nlp = spacy.load('es_core_news_sm')


import pymongo

def obtener_datos(user_id):

    mongo_uri = os.environ.get("MONGO_URI")
    mongo_client = pymongo.MongoClient(mongo_uri)
    db = mongo_client["jaguar_chat"]

    col_historial = db["historial"]


    cursor = col_historial.find({'user_id': user_id})


    prompts = [doc for doc in cursor]
    print("Datos obtenidos:", prompts)  
    return prompts

def contar_palabras(prompts, campo='prompt'):
    nlp = spacy.load("es_core_news_sm")
    conteo_palabras = defaultdict(int)

    for prompt in prompts:
        texto = prompt.get(campo)
        if texto is not None:
            doc = nlp(texto)
            for token in doc:
                if token.is_alpha:
                    conteo_palabras[token.text.lower()] += 1

    return dict(conteo_palabras)


def obtener_horario_mayor_actividad(prompts):
    conteo_horas = [0] * 24

    for prompt in prompts:
        try:
            fecha = prompt['timestamp'] if 'timestamp' in prompt else prompt['tamp']
            if isinstance(fecha, str):
                fecha_hora = datetime.strptime(fecha, "%Y-%m-%d %H:%M:%S.%f")
            else:
                fecha_hora = fecha
            hora = fecha_hora.hour
            conteo_horas[hora] += 1
        except KeyError:
            print(f"No se encontró 'timestamp' ni 'tamp' en el prompt: {prompt}")

    horas_mayor_actividad = [(i, conteo) for i, conteo in enumerate(conteo_horas)]

    return horas_mayor_actividad


def analizar_nivel_comprension(prompts):
    resultados = []

    for prompt in prompts:
        texto = prompt.get('prompt')
        if texto is not None:
            doc = nlp(texto)
            nivel_comprension = textstat.flesch_kincaid_grade(texto)
            resultados.append({'texto': texto, 'nivel_comprension': nivel_comprension})

    return resultados


def analizar_sentimientos(prompts):
    resultados = []

    for prompt in prompts:
        texto = prompt.get('prompt')
        if texto is not None:
            doc = nlp(texto)

            puntaje_sentimiento = TextBlob(texto).sentiment.polarity

        
            if puntaje_sentimiento > 0:
                etiqueta_sentimiento = "Positivo"
            elif puntaje_sentimiento < 0:
                etiqueta_sentimiento = "Negativo"
            else:
                etiqueta_sentimiento = "Neutral"

            resultados.append({'texto': texto, 'puntaje_sentimiento': puntaje_sentimiento, 'etiqueta_sentimiento': etiqueta_sentimiento})

    return resultados

def analizar_temas_mas_consultados(prompts):
    temas_contados = {}

    for prompt in prompts:
        tema = prompt.get('prompt')
        if tema is not None:
            if tema in temas_contados:
                temas_contados[tema] += 1
            else:
                temas_contados[tema] = 1

    temas_ordenados = sorted(temas_contados.items(), key=lambda x: x[1], reverse=True)

    return temas_ordenados

