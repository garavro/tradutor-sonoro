import math
import os
from collections import defaultdict

import numpy as np

from config import (
    GROUP_TOP_K,
    MIN_CONFIDENCE,
    MIN_MARGIN,
)
from database import (
    caminho_audio_real,
    modelo_contexto,
)
from audio_utils import (
    ler_wav,
    recortar_silencio,
)
from features import (
    extrair_caracteristicas_audio,
    distancia_dtw,
    distancia_para_confianca,
)


def carregar_referencias(conn):
    rows = conn.execute("""
        SELECT id, palavra, arquivo_audio
        FROM palavras
        ORDER BY id
    """).fetchall()

    refs = []

    for ident, palavra, arquivo in rows:
        caminho = caminho_audio_real(arquivo)

        if not caminho or not os.path.exists(caminho):
            continue

        try:
            audio, taxa = ler_wav(caminho)
            audio = recortar_silencio(audio, taxa)

            feat = extrair_caracteristicas_audio(
                audio,
                taxa
            )

            refs.append({
                "id": ident,
                "palavra": palavra,
                "arquivo": arquivo,
                "feat": feat,
            })

        except Exception:
            pass

    return refs


def reconhecer_audio(audio, taxa, referencias):
    consulta = extrair_caracteristicas_audio(
        audio,
        taxa
    )

    por_palavra = defaultdict(list)

    for ref in referencias:
        distancia = distancia_dtw(
            consulta,
            ref["feat"]
        )

        por_palavra[
            ref["palavra"].casefold()
        ].append({
            "palavra": ref["palavra"],
            "distancia": distancia,
            "arquivo": ref["arquivo"],
        })

    grupos = []

    for amostras in por_palavra.values():
        amostras.sort(
            key=lambda x: x["distancia"]
        )

        melhores = amostras[:GROUP_TOP_K]

        distancia = float(
            np.mean([
                item["distancia"]
                for item in melhores
            ])
        )

        grupos.append({
            "palavra": melhores[0]["palavra"],
            "distancia": distancia,
            "confianca": distancia_para_confianca(
                distancia
            ),
            "total_amostras": len(amostras),
        })

    grupos.sort(
        key=lambda x: x["distancia"]
    )

    if not grupos:
        return None, []

    melhor = grupos[0]

    if len(grupos) >= 2:
        margem = (
            melhor["confianca"]
            - grupos[1]["confianca"]
        )
    else:
        margem = melhor["confianca"]

    return {
        "palavra": melhor["palavra"],
        "confianca": melhor["confianca"],
        "margem": margem,
        "confiavel": (
            melhor["confianca"] >= MIN_CONFIDENCE
            and margem >= MIN_MARGIN
        ),
    }, grupos


def prob_contexto(
    anterior,
    atual,
    unigramas,
    bigramas
):
    anterior = anterior.casefold()
    atual = atual.casefold()

    vocab = max(1, len(unigramas))

    total_prev = sum(
        qtd
        for (a, _), qtd in bigramas.items()
        if a == anterior
    )

    cont = bigramas.get(
        (anterior, atual),
        0
    )

    return (
        cont + 1.0
    ) / (
        total_prev + vocab
    )


def ajustar_por_contexto(
    conn,
    anterior,
    grupos,
    peso_contexto=0.16
):
    """
    Reordena os 3 melhores candidatos usando as frases anteriores.
    O som continua sendo dominante.
    """
    if not grupos:
        return []

    unigramas, bigramas = modelo_contexto(conn)

    if not bigramas:
        return grupos

    ajustados = []

    for cand in grupos[:3]:
        acustico = max(
            1e-6,
            cand["confianca"] / 100.0
        )

        contexto = prob_contexto(
            anterior,
            cand["palavra"],
            unigramas,
            bigramas
        )

        score = (
            (1.0 - peso_contexto)
            * math.log(acustico)
            +
            peso_contexto
            * math.log(max(contexto, 1e-9))
        )

        novo = dict(cand)
        novo["score_contextual"] = score

        ajustados.append(novo)

    ajustados.sort(
        key=lambda x: x["score_contextual"],
        reverse=True
    )

    return ajustados
