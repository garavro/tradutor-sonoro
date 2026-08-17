from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
AUDIO_DIR = BASE_DIR / "audios"
DB_PATH = BASE_DIR / "dicionario.db"

CHANNELS = 1
ANALYSIS_RATE = 16000

DEFAULT_WORD_DURATION = 3.0

GROUP_TOP_K = 3
MIN_CONFIDENCE = 50.0
MIN_MARGIN = 4.0

# ============================================================
# MODO AO VIVO
# ============================================================

# Tamanho de cada bloco recebido do microfone.
LIVE_BLOCK_MS = 50

# Tempo mínimo de áudio antes de tentar uma previsão provisória.
LIVE_MIN_EVENT_MS = 160

# Se ficar silencioso por esse tempo, a unidade sonora é encerrada.
LIVE_END_SILENCE_MS = 180

# Evita uma gravação infinita quando não houver silêncio.
LIVE_MAX_EVENT_MS = 2200

# A cada quanto tempo atualizar a previsão provisória.
LIVE_PREVIEW_INTERVAL_MS = 250

# Número de previsões provisórias iguais para considerar o resultado estável.
LIVE_STABILITY_HITS = 2

# Confiança mínima para exibir uma previsão provisória.
LIVE_PREVIEW_MIN_CONFIDENCE = 42.0

# Após esse tempo sem novas palavras, a frase atual é considerada concluída.
LIVE_PHRASE_TIMEOUT_MS = 1300

# Multiplicador sobre o ruído ambiente para detectar atividade.
LIVE_NOISE_MULTIPLIER = 3.2

# Limite absoluto mínimo para evitar disparos em silêncio digital.
LIVE_MIN_RMS = 0.004

# Tempo usado para calibrar o ruído ao iniciar o modo ao vivo.
LIVE_CALIBRATION_SECONDS = 1.5

AUDIO_DIR.mkdir(exist_ok=True)
