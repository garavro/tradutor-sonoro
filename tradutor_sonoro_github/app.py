import os
import shutil
import uuid

import sounddevice as sd

from config import (
    AUDIO_DIR,
    BASE_DIR,
    DEFAULT_WORD_DURATION,
)
from database import (
    conectar,
    caminho_audio_real,
    caminho_para_banco,
    listar_amostras,
    listar_grupos,
)
from audio_utils import (
    gravar_audio,
    reproduzir_audio,
)
from recognizer import (
    carregar_referencias,
    reconhecer_audio,
)
from live_translator import (
    TradutorAoVivo,
)


def cadastrar(conn):
    print(
        "\n=== CADASTRAR AMOSTRA ==="
    )

    palavra = input(
        "Tradução/palavra: "
    ).strip()

    if not palavra:
        print("Palavra vazia.")
        return

    caminho = (
        AUDIO_DIR
        / f"{uuid.uuid4().hex}.wav"
    )

    input(
        "Pressione Enter para gravar..."
    )

    try:
        gravar_audio(
            caminho,
            DEFAULT_WORD_DURATION
        )
    except Exception as erro:
        print(
            f"Erro ao gravar: {erro}"
        )
        return

    ouvir = input(
        "Ouvir antes de salvar? [s/N]: "
    ).strip().lower()

    if ouvir == "s":
        reproduzir_audio(
            caminho
        )

    observacao = input(
        "Observação [Enter para ignorar]: "
    ).strip()

    conn.execute("""
        INSERT INTO palavras (
            palavra,
            arquivo_audio,
            observacao
        )
        VALUES (?, ?, ?)
    """, (
        palavra,
        caminho_para_banco(caminho),
        observacao or None
    ))

    conn.commit()

    print(
        f'Salvo como "{palavra}".'
    )


def treinar(conn):
    print(
        "\n=== TREINAR PALAVRA ==="
    )

    palavra = input(
        "Palavra/tradução: "
    ).strip()

    if not palavra:
        return

    qtd_txt = input(
        "Quantidade de amostras "
        "[Enter = 5]: "
    ).strip()

    try:
        qtd = (
            int(qtd_txt)
            if qtd_txt
            else 5
        )

        if qtd <= 0:
            raise ValueError
    except ValueError:
        print(
            "Quantidade inválida."
        )
        return

    for i in range(
        1,
        qtd + 1
    ):
        caminho = (
            AUDIO_DIR
            / f"{uuid.uuid4().hex}.wav"
        )

        input(
            f"\nAmostra {i}/{qtd}. "
            "Pressione Enter..."
        )

        try:
            gravar_audio(
                caminho,
                DEFAULT_WORD_DURATION
            )

            conn.execute("""
                INSERT INTO palavras (
                    palavra,
                    arquivo_audio,
                    observacao
                )
                VALUES (?, ?, ?)
            """, (
                palavra,
                caminho_para_banco(caminho),
                f"Treinamento v0.7 {i}/{qtd}"
            ))

            conn.commit()

        except Exception as erro:
            print(
                f"Erro: {erro}"
            )

            if caminho.exists():
                caminho.unlink()

    print(
        "Treinamento concluído."
    )


def modo_ao_vivo(conn):
    referencias = carregar_referencias(
        conn
    )

    if not referencias:
        print(
            "\nO dicionário está vazio."
        )

        print(
            "Cadastre ou treine palavras primeiro."
        )
        return

    print(
        f"\n{len(referencias)} amostra(s) "
        "carregada(s) na memória."
    )

    print(
        "Isso evita reler o banco a cada bloco de áudio."
    )

    tradutor = TradutorAoVivo(
        conn,
        referencias
    )

    tradutor.executar()


def mostrar_dicionario(conn):
    grupos = listar_grupos(
        conn
    )

    print(
        "\n=== DICIONÁRIO ==="
    )

    if not grupos:
        print("Vazio.")
        return

    total = 0

    for palavra, qtd in grupos:
        print(
            f"{palavra} -> "
            f"{qtd} amostra(s)"
        )

        total += qtd

    print(
        f"\n{len(grupos)} palavra(s), "
        f"{total} amostra(s)."
    )


def historico_ao_vivo(conn):
    rows = conn.execute("""
        SELECT
            id,
            palavra,
            confianca,
            frase_parcial,
            criado_em
        FROM historico_ao_vivo
        ORDER BY id DESC
        LIMIT 40
    """).fetchall()

    print(
        "\n=== HISTÓRICO AO VIVO ==="
    )

    if not rows:
        print(
            "Nenhum reconhecimento ao vivo."
        )
        return

    for (
        ident,
        palavra,
        confianca,
        frase,
        criado
    ) in rows:
        print(
            f"{ident:03d} | "
            f"{palavra} | "
            f"{confianca or 0:.1f}% | "
            f"{frase} | "
            f"{criado}"
        )


def dispositivos():
    print(
        "\n=== DISPOSITIVOS ==="
    )

    print(
        sd.query_devices()
    )

    print(
        "\nPadrão:",
        sd.default.device
    )


def excluir(conn):
    rows = listar_amostras(
        conn
    )

    if not rows:
        print(
            "Nenhuma amostra."
        )
        return

    for (
        ident,
        palavra,
        arquivo,
        obs,
        criado
    ) in rows:
        print(
            f"{ident:03d} | "
            f"{palavra} | "
            f"{obs or '-'}"
        )

    txt = input(
        "\nID para excluir "
        "[Enter cancela]: "
    ).strip()

    if not txt:
        return

    try:
        ident = int(txt)

    except ValueError:
        print(
            "ID inválido."
        )
        return

    row = conn.execute("""
        SELECT palavra, arquivo_audio
        FROM palavras
        WHERE id = ?
    """, (ident,)).fetchone()

    if not row:
        print(
            "Não encontrado."
        )
        return

    palavra, arquivo = row

    confirmar = input(
        f'Excluir amostra de '
        f'"{palavra}"? [s/N]: '
    ).strip().lower()

    if confirmar != "s":
        return

    conn.execute(
        "DELETE FROM palavras WHERE id = ?",
        (ident,)
    )

    conn.commit()

    caminho = caminho_audio_real(
        arquivo
    )

    if (
        caminho
        and os.path.exists(caminho)
    ):
        try:
            os.remove(caminho)
        except OSError:
            pass

    print(
        "Excluído."
    )


def menu():
    conn = conectar()

    try:
        while True:
            print("""
========================================
       TRADUTOR SONORO v0.7
========================================
1 - Cadastrar uma amostra
2 - Treinar uma palavra
3 - TRADUÇÃO AO VIVO
4 - Mostrar dicionário
5 - Histórico ao vivo
6 - Mostrar dispositivos de áudio
7 - Excluir uma amostra
0 - Sair
""")

            op = input(
                "Escolha: "
            ).strip()

            if op == "1":
                cadastrar(
                    conn
                )

            elif op == "2":
                treinar(
                    conn
                )

            elif op == "3":
                modo_ao_vivo(
                    conn
                )

            elif op == "4":
                mostrar_dicionario(
                    conn
                )

            elif op == "5":
                historico_ao_vivo(
                    conn
                )

            elif op == "6":
                dispositivos()

            elif op == "7":
                excluir(
                    conn
                )

            elif op == "0":
                print(
                    "Encerrando."
                )
                break

            else:
                print(
                    "Opção inválida."
                )

    finally:
        conn.close()


if __name__ == "__main__":
    menu()
