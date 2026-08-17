import os
import sqlite3
from collections import Counter

from config import BASE_DIR, AUDIO_DIR, DB_PATH


def conectar():
    conn = sqlite3.connect(DB_PATH)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS palavras (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            palavra TEXT NOT NULL,
            arquivo_audio TEXT NOT NULL UNIQUE,
            observacao TEXT,
            criado_em TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS historico_reconhecimento (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            palavra_prevista TEXT,
            confianca REAL,
            margem REAL,
            status TEXT,
            palavra_correta TEXT,
            criado_em TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS historico_frases (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            frase_prevista TEXT NOT NULL,
            frase_corrigida TEXT,
            quantidade_segmentos INTEGER NOT NULL,
            confianca_media REAL,
            criado_em TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS historico_ao_vivo (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            palavra TEXT NOT NULL,
            confianca REAL,
            frase_parcial TEXT,
            criado_em TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()
    return conn


def caminho_audio_real(valor_banco):
    if not valor_banco:
        return None

    p = str(valor_banco)

    if os.path.exists(p):
        return p

    alternativo = AUDIO_DIR / os.path.basename(p)
    if alternativo.exists():
        return str(alternativo)

    relativo = BASE_DIR / p
    if relativo.exists():
        return str(relativo)

    return p


def caminho_para_banco(caminho):
    return os.path.relpath(str(caminho), str(BASE_DIR))


def listar_grupos(conn):
    return conn.execute("""
        SELECT palavra, COUNT(*)
        FROM palavras
        GROUP BY palavra COLLATE NOCASE
        ORDER BY palavra COLLATE NOCASE
    """).fetchall()


def listar_amostras(conn):
    return conn.execute("""
        SELECT id, palavra, arquivo_audio, observacao, criado_em
        FROM palavras
        ORDER BY palavra COLLATE NOCASE, id
    """).fetchall()


def registrar_frase(conn, prevista, corrigida, qtd, confianca):
    conn.execute("""
        INSERT INTO historico_frases (
            frase_prevista,
            frase_corrigida,
            quantidade_segmentos,
            confianca_media
        )
        VALUES (?, ?, ?, ?)
    """, (
        prevista,
        corrigida,
        qtd,
        confianca,
    ))
    conn.commit()


def registrar_ao_vivo(conn, palavra, confianca, frase_parcial):
    conn.execute("""
        INSERT INTO historico_ao_vivo (
            palavra,
            confianca,
            frase_parcial
        )
        VALUES (?, ?, ?)
    """, (
        palavra,
        confianca,
        frase_parcial,
    ))
    conn.commit()


def carregar_frases_confirmadas(conn):
    rows = conn.execute("""
        SELECT frase_prevista, frase_corrigida
        FROM historico_frases
        ORDER BY id
    """).fetchall()

    frases = []

    for prevista, corrigida in rows:
        frase = (corrigida or prevista or "").strip()

        if frase:
            frases.append(frase)

    return frases


def modelo_contexto(conn):
    frases = carregar_frases_confirmadas(conn)

    unigramas = Counter()
    bigramas = Counter()

    for frase in frases:
        palavras = frase.split()
        seq = ["<s>"] + palavras + ["</s>"]

        for palavra in palavras:
            unigramas[palavra.casefold()] += 1

        for a, b in zip(seq, seq[1:]):
            bigramas[(a.casefold(), b.casefold())] += 1

    return unigramas, bigramas
