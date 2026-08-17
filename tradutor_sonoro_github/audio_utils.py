import wave

import numpy as np
import sounddevice as sd

from config import CHANNELS


def obter_dispositivo_entrada():
    dispositivo = sd.query_devices(kind="input")

    if dispositivo["max_input_channels"] < 1:
        raise RuntimeError("Nenhum canal de entrada disponível.")

    taxa = int(round(dispositivo["default_samplerate"]))

    sd.check_input_settings(
        device=None,
        channels=CHANNELS,
        dtype="float32",
        samplerate=taxa,
    )

    return dispositivo, taxa


def gravar_audio(caminho, duracao, mostrar_info=True):
    dispositivo, taxa = obter_dispositivo_entrada()

    if mostrar_info:
        print(f"\nEntrada: {dispositivo['name']}")
        print(f"Taxa: {taxa} Hz")
        print(f"Gravando por {duracao:.1f} s...")

    audio = sd.rec(
        int(duracao * taxa),
        samplerate=taxa,
        channels=CHANNELS,
        dtype="float32",
    )

    sd.wait()

    salvar_wav_float(
        caminho,
        audio.reshape(-1),
        taxa
    )

    if mostrar_info:
        print("Gravação concluída.")


def salvar_wav_float(caminho, audio, taxa):
    audio = np.asarray(audio, dtype=np.float32).reshape(-1)
    audio = np.clip(audio, -1.0, 1.0)

    pcm = (audio * 32767.0).astype(np.int16)

    with wave.open(str(caminho), "wb") as arq:
        arq.setnchannels(1)
        arq.setsampwidth(2)
        arq.setframerate(int(taxa))
        arq.writeframes(pcm.tobytes())


def ler_wav(caminho):
    with wave.open(str(caminho), "rb") as arq:
        canais = arq.getnchannels()
        taxa = arq.getframerate()
        largura = arq.getsampwidth()
        frames = arq.readframes(arq.getnframes())

    if largura != 2:
        raise ValueError("Apenas WAV PCM 16 bits é suportado.")

    audio = np.frombuffer(
        frames,
        dtype=np.int16
    ).astype(np.float32)

    if canais > 1:
        audio = audio.reshape(-1, canais).mean(axis=1)

    audio /= 32768.0

    return audio, taxa


def reproduzir_audio(caminho):
    audio, taxa = ler_wav(caminho)

    try:
        sd.check_output_settings(
            device=None,
            channels=1,
            dtype="float32",
            samplerate=taxa,
        )
    except Exception:
        saida = sd.query_devices(kind="output")
        taxa_saida = int(round(saida["default_samplerate"]))
        audio = reamostrar(audio, taxa, taxa_saida)
        taxa = taxa_saida

    sd.play(
        audio.astype(np.float32),
        samplerate=taxa
    )
    sd.wait()


def reamostrar(audio, taxa_origem, taxa_destino):
    if taxa_origem == taxa_destino:
        return np.asarray(audio, dtype=np.float32)

    if len(audio) < 2:
        return np.asarray(audio, dtype=np.float32)

    duracao = len(audio) / float(taxa_origem)
    novo_tamanho = max(
        1,
        int(round(duracao * taxa_destino))
    )

    x_antigo = np.linspace(
        0.0,
        1.0,
        len(audio),
        endpoint=False
    )

    x_novo = np.linspace(
        0.0,
        1.0,
        novo_tamanho,
        endpoint=False
    )

    return np.interp(
        x_novo,
        x_antigo,
        audio
    ).astype(np.float32)


def normalizar(audio):
    audio = np.asarray(
        audio,
        dtype=np.float32
    ).copy()

    if len(audio) == 0:
        return audio

    audio -= float(np.mean(audio))

    pico = float(np.max(np.abs(audio)))

    if pico > 1e-7:
        audio /= pico

    return audio


def recortar_silencio(audio, taxa):
    audio = np.asarray(audio, dtype=np.float32)

    if len(audio) == 0:
        return audio

    janela = max(1, int(0.020 * taxa))
    salto = max(1, int(0.010 * taxa))

    if len(audio) < janela:
        return audio

    rms = []
    inicios = []

    for inicio in range(
        0,
        len(audio) - janela + 1,
        salto
    ):
        trecho = audio[inicio:inicio + janela]

        energia = float(
            np.sqrt(
                np.mean(trecho * trecho) + 1e-12
            )
        )

        rms.append(energia)
        inicios.append(inicio)

    rms = np.asarray(rms, dtype=np.float32)
    pico = float(np.max(rms))

    if pico < 1e-6:
        return audio

    ruido = float(np.percentile(rms, 20))

    limiar = max(
        0.0025,
        ruido * 2.4,
        pico * 0.07
    )

    ativos = np.where(rms >= limiar)[0]

    if len(ativos) == 0:
        return audio

    margem = int(0.05 * taxa)

    ini = max(
        0,
        inicios[int(ativos[0])] - margem
    )

    fim = min(
        len(audio),
        inicios[int(ativos[-1])] + janela + margem
    )

    return audio[ini:fim]
