import queue
import sys
import threading
import time

import numpy as np
import sounddevice as sd

from config import (
    LIVE_BLOCK_MS,
    LIVE_MIN_EVENT_MS,
    LIVE_END_SILENCE_MS,
    LIVE_MAX_EVENT_MS,
    LIVE_PREVIEW_INTERVAL_MS,
    LIVE_STABILITY_HITS,
    LIVE_PREVIEW_MIN_CONFIDENCE,
    LIVE_PHRASE_TIMEOUT_MS,
    LIVE_NOISE_MULTIPLIER,
    LIVE_MIN_RMS,
    LIVE_CALIBRATION_SECONDS,
)
from database import (
    registrar_ao_vivo,
    registrar_frase,
)
from recognizer import (
    reconhecer_audio,
    ajustar_por_contexto,
)


class TradutorAoVivo:
    def __init__(
        self,
        conn,
        referencias,
        dispositivo=None
    ):
        self.conn = conn
        self.referencias = referencias
        self.dispositivo = dispositivo

        info = sd.query_devices(
            dispositivo,
            "input"
        )

        self.taxa = int(
            round(
                info["default_samplerate"]
            )
        )

        self.blocksize = max(
            1,
            int(
                self.taxa
                * LIVE_BLOCK_MS
                / 1000.0
            )
        )

        self.fila = queue.Queue(
            maxsize=200
        )

        self.parar = threading.Event()

        self.noise_rms = LIVE_MIN_RMS
        self.threshold = LIVE_MIN_RMS

        self.ativo = False
        self.blocos_evento = []
        self.silencio_ms = 0.0
        self.evento_ms = 0.0

        self.ultima_preview_em = 0.0
        self.ultima_preview_palavra = None
        self.preview_hits = 0

        self.frase = []
        self.confiancas_frase = []
        self.ultima_palavra_em = None

        self.total_confirmadas = 0
        self.total_descartadas = 0

    def callback(
        self,
        indata,
        frames,
        time_info,
        status
    ):
        if status:
            # Não imprimir aqui para manter o callback leve.
            pass

        bloco = np.asarray(
            indata[:, 0],
            dtype=np.float32
        ).copy()

        try:
            self.fila.put_nowait(
                bloco
            )
        except queue.Full:
            # Descartamos o bloco mais antigo para evitar travar o áudio.
            try:
                self.fila.get_nowait()
            except queue.Empty:
                pass

            try:
                self.fila.put_nowait(
                    bloco
                )
            except queue.Full:
                pass

    @staticmethod
    def rms(bloco):
        return float(
            np.sqrt(
                np.mean(
                    bloco * bloco
                ) + 1e-12
            )
        )

    def calibrar(self):
        print(
            "\nCalibrando ruído ambiente..."
        )
        print(
            "Fique em silêncio por "
            f"{LIVE_CALIBRATION_SECONDS:.1f} segundo(s)."
        )

        amostras = []

        total_blocos = max(
            1,
            int(
                LIVE_CALIBRATION_SECONDS
                * 1000.0
                / LIVE_BLOCK_MS
            )
        )

        while len(amostras) < total_blocos:
            try:
                bloco = self.fila.get(
                    timeout=1.0
                )
            except queue.Empty:
                continue

            amostras.append(
                self.rms(bloco)
            )

        mediana = float(
            np.median(amostras)
        )

        p90 = float(
            np.percentile(
                amostras,
                90
            )
        )

        self.noise_rms = max(
            mediana,
            1e-6
        )

        self.threshold = max(
            LIVE_MIN_RMS,
            p90 * LIVE_NOISE_MULTIPLIER,
            self.noise_rms
            * LIVE_NOISE_MULTIPLIER
        )

        print(
            f"Ruído estimado: "
            f"{self.noise_rms:.5f}"
        )

        print(
            f"Limiar de atividade: "
            f"{self.threshold:.5f}"
        )

        print(
            "\n🎤 Ouvindo..."
        )
        print(
            "Pressione Ctrl+C para sair do modo ao vivo."
        )

    def atualizar_ruido(
        self,
        nivel
    ):
        """
        Adaptação lenta ao ambiente enquanto não existe atividade.
        """
        if self.ativo:
            return

        if nivel < self.threshold:
            self.noise_rms = (
                0.995 * self.noise_rms
                + 0.005 * nivel
            )

            self.threshold = max(
                LIVE_MIN_RMS,
                self.noise_rms
                * LIVE_NOISE_MULTIPLIER
            )

    def exibir_estado(
        self,
        provisoria=None,
        confianca=None
    ):
        frase = " ".join(
            self.frase
        )

        sys.stdout.write(
            "\r" + " " * 120 + "\r"
        )

        if provisoria:
            texto = (
                f'🎤 "{frase}" '
                f'[{provisoria}? {confianca:.0f}%]'
            )
        else:
            texto = (
                f'🎤 "{frase}"'
                if frase
                else "🎤 Ouvindo..."
            )

        sys.stdout.write(
            texto
        )

        sys.stdout.flush()

    def reconhecer_evento(
        self,
        audio,
        provisoria=False
    ):
        if len(audio) < int(
            self.taxa
            * LIVE_MIN_EVENT_MS
            / 1000.0
        ):
            return None, []

        try:
            resultado, grupos = reconhecer_audio(
                audio,
                self.taxa,
                self.referencias
            )

        except Exception:
            return None, []

        if not resultado:
            return None, []

        anterior = (
            self.frase[-1]
            if self.frase
            else "<s>"
        )

        contextual = ajustar_por_contexto(
            self.conn,
            anterior,
            grupos
        )

        if contextual:
            escolhido = contextual[0]

            resultado = dict(
                resultado
            )

            resultado["palavra"] = (
                escolhido["palavra"]
            )

            resultado["confianca"] = (
                escolhido["confianca"]
            )

        return resultado, grupos

    def preview(
        self,
        audio
    ):
        agora = time.monotonic()

        if (
            agora
            - self.ultima_preview_em
            < LIVE_PREVIEW_INTERVAL_MS
            / 1000.0
        ):
            return

        self.ultima_preview_em = agora

        resultado, _ = (
            self.reconhecer_evento(
                audio,
                provisoria=True
            )
        )

        if not resultado:
            return

        if (
            resultado["confianca"]
            < LIVE_PREVIEW_MIN_CONFIDENCE
        ):
            return

        palavra = resultado[
            "palavra"
        ]

        if (
            palavra
            == self.ultima_preview_palavra
        ):
            self.preview_hits += 1
        else:
            self.ultima_preview_palavra = (
                palavra
            )

            self.preview_hits = 1

        if (
            self.preview_hits
            >= LIVE_STABILITY_HITS
        ):
            self.exibir_estado(
                provisoria=palavra,
                confianca=resultado[
                    "confianca"
                ]
            )

    def confirmar_evento(
        self,
        audio
    ):
        resultado, grupos = (
            self.reconhecer_evento(
                audio
            )
        )

        self.ultima_preview_palavra = None
        self.preview_hits = 0

        if not resultado:
            self.total_descartadas += 1
            self.exibir_estado()
            return

        palavra = resultado[
            "palavra"
        ]

        confianca = resultado[
            "confianca"
        ]

        if (
            confianca
            < LIVE_PREVIEW_MIN_CONFIDENCE
        ):
            self.total_descartadas += 1
            self.exibir_estado()
            return

        self.frase.append(
            palavra
        )

        self.confiancas_frase.append(
            confianca
        )

        self.total_confirmadas += 1

        self.ultima_palavra_em = (
            time.monotonic()
        )

        frase_parcial = " ".join(
            self.frase
        )

        registrar_ao_vivo(
            self.conn,
            palavra,
            confianca,
            frase_parcial
        )

        sys.stdout.write(
            "\r" + " " * 120 + "\r"
        )

        print(
            f"✓ {palavra} "
            f"({confianca:.1f}%)"
        )

        self.exibir_estado()

    def finalizar_frase(
        self
    ):
        if not self.frase:
            return

        frase = " ".join(
            self.frase
        )

        confianca = float(
            np.mean(
                self.confiancas_frase
            )
        ) if self.confiancas_frase else 0.0

        sys.stdout.write(
            "\r" + " " * 120 + "\r"
        )

        print(
            "\n========================================"
        )

        print(
            "FRASE AO VIVO:"
        )

        print(
            frase
        )

        print(
            f"Confiança média: "
            f"{confianca:.1f}%"
        )

        print(
            "========================================"
        )

        registrar_frase(
            self.conn,
            frase,
            frase,
            len(self.frase),
            confianca
        )

        self.frase = []
        self.confiancas_frase = []
        self.ultima_palavra_em = None

        print(
            "\n🎤 Ouvindo nova frase..."
        )

    def processar_bloco(
        self,
        bloco
    ):
        nivel = self.rms(
            bloco
        )

        atividade = (
            nivel >= self.threshold
        )

        self.atualizar_ruido(
            nivel
        )

        if not self.ativo:
            if atividade:
                self.ativo = True
                self.blocos_evento = [
                    bloco
                ]

                self.silencio_ms = 0.0
                self.evento_ms = (
                    LIVE_BLOCK_MS
                )

                self.ultima_preview_em = 0.0

            else:
                if (
                    self.frase
                    and self.ultima_palavra_em
                    and (
                        time.monotonic()
                        - self.ultima_palavra_em
                        >= LIVE_PHRASE_TIMEOUT_MS
                        / 1000.0
                    )
                ):
                    self.finalizar_frase()

            return

        self.blocos_evento.append(
            bloco
        )

        self.evento_ms += (
            LIVE_BLOCK_MS
        )

        if atividade:
            self.silencio_ms = 0.0
        else:
            self.silencio_ms += (
                LIVE_BLOCK_MS
            )

        audio_evento = np.concatenate(
            self.blocos_evento
        )

        if atividade:
            self.preview(
                audio_evento
            )

        encerrar = (
            self.silencio_ms
            >= LIVE_END_SILENCE_MS
            or self.evento_ms
            >= LIVE_MAX_EVENT_MS
        )

        if encerrar:
            silencio_amostras = int(
                self.taxa
                * min(
                    self.silencio_ms,
                    LIVE_END_SILENCE_MS
                )
                / 1000.0
            )

            if (
                silencio_amostras > 0
                and len(audio_evento)
                > silencio_amostras
            ):
                audio_evento = (
                    audio_evento[
                        :-silencio_amostras
                    ]
                )

            self.confirmar_evento(
                audio_evento
            )

            self.ativo = False
            self.blocos_evento = []
            self.silencio_ms = 0.0
            self.evento_ms = 0.0

    def executar(self):
        print(
            "\n========================================"
        )

        print(
            "     TRADUTOR SONORO AO VIVO v0.7"
        )

        print(
            "========================================"
        )

        print(
            "O microfone permanecerá aberto."
        )

        print(
            "Produza um som, faça uma pausa curta "
            "e continue com o próximo."
        )

        try:
            with sd.InputStream(
                device=self.dispositivo,
                channels=1,
                samplerate=self.taxa,
                blocksize=self.blocksize,
                dtype="float32",
                callback=self.callback,
            ):
                self.calibrar()

                while not self.parar.is_set():
                    try:
                        bloco = self.fila.get(
                            timeout=0.1
                        )
                    except queue.Empty:
                        continue

                    self.processar_bloco(
                        bloco
                    )

        except KeyboardInterrupt:
            pass

        finally:
            if self.ativo and self.blocos_evento:
                audio = np.concatenate(
                    self.blocos_evento
                )

                self.confirmar_evento(
                    audio
                )

            self.finalizar_frase()

            print(
                "\nModo ao vivo encerrado."
            )

            print(
                f"Palavras confirmadas: "
                f"{self.total_confirmadas}"
            )

            print(
                f"Eventos descartados: "
                f"{self.total_descartadas}"
            )
