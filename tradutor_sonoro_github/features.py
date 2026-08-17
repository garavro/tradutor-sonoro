import math

import numpy as np

from config import ANALYSIS_RATE
from audio_utils import (
    ler_wav,
    recortar_silencio,
    normalizar,
    reamostrar,
)


def hz_para_mel(hz):
    return 2595.0 * np.log10(
        1.0 + hz / 700.0
    )


def mel_para_hz(mel):
    return 700.0 * (
        10.0 ** (mel / 2595.0) - 1.0
    )


def filtros_mel(
    taxa,
    n_fft,
    quantidade=26,
    freq_min=80.0
):
    freq_max = taxa / 2.0

    pontos_mel = np.linspace(
        hz_para_mel(freq_min),
        hz_para_mel(freq_max),
        quantidade + 2
    )

    pontos_hz = mel_para_hz(pontos_mel)

    bins = np.floor(
        (n_fft + 1) * pontos_hz / taxa
    ).astype(int)

    max_bin = n_fft // 2

    bins = np.clip(
        bins,
        0,
        max_bin
    )

    filtros = np.zeros(
        (quantidade, max_bin + 1),
        dtype=np.float32
    )

    for m in range(1, quantidade + 1):
        e = bins[m - 1]
        c = bins[m]
        d = bins[m + 1]

        if c <= e:
            c = min(e + 1, max_bin)

        if d <= c:
            d = min(c + 1, max_bin)

        if c > e:
            for k in range(e, c):
                filtros[m - 1, k] = (
                    (k - e) / float(c - e)
                )

        if d > c:
            for k in range(c, d):
                filtros[m - 1, k] = (
                    (d - k) / float(d - c)
                )

    return filtros


def matriz_dct(n_mfcc, n_filtros):
    matriz = np.zeros(
        (n_mfcc, n_filtros),
        dtype=np.float32
    )

    fator = math.pi / float(n_filtros)

    for i in range(n_mfcc):
        for j in range(n_filtros):
            matriz[i, j] = math.cos(
                (j + 0.5) * i * fator
            )

    matriz[0] *= math.sqrt(1.0 / n_filtros)

    if n_mfcc > 1:
        matriz[1:] *= math.sqrt(2.0 / n_filtros)

    return matriz


def criar_frames(audio, tamanho, salto):
    if len(audio) < tamanho:
        audio = np.pad(
            audio,
            (0, tamanho - len(audio))
        )

    qtd = 1 + int(
        math.ceil(
            (len(audio) - tamanho) / float(salto)
        )
    )

    total = (qtd - 1) * salto + tamanho

    if total > len(audio):
        audio = np.pad(
            audio,
            (0, total - len(audio))
        )

    indices = (
        np.tile(
            np.arange(tamanho),
            (qtd, 1)
        )
        +
        np.tile(
            np.arange(qtd) * salto,
            (tamanho, 1)
        ).T
    )

    return audio[indices]


def extrair_caracteristicas_audio(audio, taxa):
    audio = recortar_silencio(audio, taxa)
    audio = normalizar(audio)
    audio = reamostrar(audio, taxa, ANALYSIS_RATE)

    if len(audio) < int(0.10 * ANALYSIS_RATE):
        raise ValueError("Áudio curto demais.")

    pre = np.empty_like(audio)

    pre[0] = audio[0]
    pre[1:] = audio[1:] - 0.97 * audio[:-1]

    frame_len = int(0.025 * ANALYSIS_RATE)
    frame_hop = int(0.010 * ANALYSIS_RATE)
    n_fft = 512

    frames = criar_frames(
        pre,
        frame_len,
        frame_hop
    )

    frames *= np.hanning(
        frame_len
    ).astype(np.float32)

    espectro = np.fft.rfft(
        frames,
        n=n_fft,
        axis=1
    )

    potencia = (
        np.abs(espectro) ** 2
    ) / float(n_fft)

    banco = filtros_mel(
        ANALYSIS_RATE,
        n_fft,
        26
    )

    mel = np.maximum(
        np.dot(
            potencia,
            banco.T
        ),
        1e-10
    )

    log_mel = np.log(mel)

    dct = matriz_dct(13, 26)

    mfcc = np.dot(
        log_mel,
        dct.T
    ).astype(np.float32)

    mfcc = mfcc[:, 1:13]

    media = np.mean(
        mfcc,
        axis=0,
        keepdims=True
    )

    desvio = np.std(
        mfcc,
        axis=0,
        keepdims=True
    )

    mfcc = (
        mfcc - media
    ) / np.maximum(
        desvio,
        1e-5
    )

    delta = np.zeros_like(mfcc)

    if len(mfcc) >= 3:
        delta[1:-1] = (
            mfcc[2:] - mfcc[:-2]
        ) * 0.5

        delta[0] = mfcc[1] - mfcc[0]
        delta[-1] = mfcc[-1] - mfcc[-2]

    return np.concatenate(
        [mfcc, delta],
        axis=1
    ).astype(np.float32)


def extrair_caracteristicas(caminho):
    audio, taxa = ler_wav(caminho)

    return extrair_caracteristicas_audio(
        audio,
        taxa
    )


def distancia_local(a, b):
    return float(
        np.linalg.norm(a - b) / math.sqrt(len(a))
    )


def distancia_dtw(a, b):
    n = len(a)
    m = len(b)

    if n == 0 or m == 0:
        return float("inf")

    janela = max(
        abs(n - m),
        int(max(n, m) * 0.35)
    )

    custo = np.full(
        (n + 1, m + 1),
        float("inf"),
        dtype=np.float64
    )

    passos = np.zeros(
        (n + 1, m + 1),
        dtype=np.int32
    )

    custo[0, 0] = 0.0

    for i in range(1, n + 1):
        j0 = max(1, i - janela)
        j1 = min(m, i + janela)

        for j in range(j0, j1 + 1):
            local = distancia_local(
                a[i - 1],
                b[j - 1]
            )

            candidatos = (
                (
                    custo[i - 1, j - 1],
                    passos[i - 1, j - 1]
                ),
                (
                    custo[i - 1, j] + 0.03,
                    passos[i - 1, j]
                ),
                (
                    custo[i, j - 1] + 0.03,
                    passos[i, j - 1]
                ),
            )

            melhor, p = min(
                candidatos,
                key=lambda x: x[0]
            )

            custo[i, j] = local + melhor
            passos[i, j] = p + 1

    if not np.isfinite(custo[n, m]):
        return float("inf")

    comprimento = max(
        1,
        int(passos[n, m])
    )

    return float(
        custo[n, m] / comprimento
    )


def distancia_para_confianca(distancia):
    if not np.isfinite(distancia):
        return 0.0

    confianca = (
        100.0
        * math.exp(-1.35 * distancia)
    )

    return max(
        0.0,
        min(100.0, confianca)
    )
