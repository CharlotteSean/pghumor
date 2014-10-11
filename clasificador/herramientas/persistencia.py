# coding=utf-8
from __future__ import absolute_import

import mysql.connector
from progress.bar import Bar

from clasificador.herramientas.define import DB_HOST, DB_USER, DB_PASS, DB_NAME
from clasificador.realidad.tweet import Tweet


def cargar_tweets():
    """Carga todos los tweets, inclusive aquellos para evaluación, aunque no se quiera evaluar,
    y aquellos mal votados, así se calculan las features para todos. Que el filtro se haga luego.

    """
    conexion = mysql.connector.connect(user=DB_USER, password=DB_PASS, host=DB_HOST, database=DB_NAME)
    cursor = conexion.cursor(buffered=True)  # buffered así sé la cantidad que son antes de iterarlos

    # TODO: tendría que traer todos, y después filtrar por los que tienen menos de 25%, así calculo las features para todos

    consulta = """
    SELECT id_account,
           T.id_tweet,
           text_tweet,
           favorite_count_tweet,
           retweet_count_tweet,
           eschiste_tweet,
           name_account,
           followers_count_account,
           evaluacion,
           votos,
           votos_no_humor_u_omitido
    FROM   tweets AS T
           NATURAL JOIN twitter_accounts
                        LEFT JOIN (SELECT id_tweet,
                                          Count(*) AS votos,
                                          Sum(CASE
                                                WHEN voto = 'x'
                                                      OR voto = 'n' THEN 1
                                                ELSE 0
                                              end) AS votos_no_humor_u_omitido
                                   FROM   votos
                                   GROUP  BY id_tweet) V
                               ON ( V.id_tweet = T.id_tweet );
    """

    cursor.execute(consulta)

    bar = Bar('Cargando tweets', max=cursor.rowcount, suffix='%(index)d/%(max)d - %(percent).2f%% - ETA: %(eta)ds')
    bar.next(0)

    resultado = {}

    for (id_account, tweet_id, texto, favoritos, retweets, es_humor, cuenta, seguidores, evaluacion, votos,
         votos_no_humor_u_omitido) in cursor:
        tw = Tweet()
        tw.id = tweet_id
        tw.texto_original = texto
        tw.texto = texto
        tw.favoritos = favoritos
        tw.retweets = retweets
        tw.es_humor = es_humor
        tw.cuenta = cuenta
        tw.seguidores = seguidores
        tw.evaluacion = evaluacion
        tw.votos = votos
        tw.votos_no_humor_u_omitido = votos_no_humor_u_omitido

        resultado[tw.id] = tw
        bar.next()

    bar.finish()

    consulta = """
    SELECT T.id_tweet,
           nombre_feature,
           valor_feature,
           votos,
           votos_no_humor_u_omitido,
           eschiste_tweet
    FROM   features
           NATURAL JOIN tweets AS T
                        LEFT JOIN (SELECT id_tweet,
                                          Count(*) AS votos,
                                          Sum(CASE
                                                WHEN voto = 'x'
                                                      OR voto = 'n' THEN 1
                                                ELSE 0
                                              end) AS votos_no_humor_u_omitido
                                   FROM   votos
                                   GROUP  BY id_tweet) V
                               ON ( V.id_tweet = T.id_tweet );
    """

    cursor.execute(consulta)

    bar = Bar('Cargando features', max=cursor.rowcount, suffix='%(index)d/%(max)d - %(percent).2f%% - ETA: %(eta)ds')
    bar.next(0)

    for (id_tweet, nombre_feature, valor_feature, votos, votos_no_humor_u_omitido, es_humor) in cursor:
        resultado[id_tweet].features[nombre_feature] = valor_feature
        bar.next()

    bar.finish()

    cursor.close()
    conexion.close()

    return list(resultado.values())


def guardar_features(tweets, **opciones):
    nombre_feature = opciones.pop('nombre_feature', None)
    conexion = mysql.connector.connect(user=DB_USER, password=DB_PASS, host=DB_HOST, database=DB_NAME)
    cursor = conexion.cursor()

    consulta = "INSERT INTO features VALUES (%s, %s, %s) ON DUPLICATE KEY UPDATE valor_feature = %s"

    if nombre_feature is None:
        mensaje = 'Guardando features'
    else:
        mensaje = 'Guardando feature ' + nombre_feature

    bar = Bar(mensaje, max=len(tweets), suffix='%(index)d/%(max)d - %(percent).2f%% - ETA: %(eta)ds')
    bar.next(0)

    for tweet in tweets:
        if nombre_feature is None:
            for key, value in tweet.features.items():
                cursor.execute(consulta, (tweet.id, key, value, value))
        else:
            cursor.execute(consulta,
                           (tweet.id, nombre_feature, tweet.features[nombre_feature], tweet.features[nombre_feature]))
        bar.next()

    conexion.commit()
    bar.finish()

    cursor.close()
    conexion.close()
    conexion.disconnect()
