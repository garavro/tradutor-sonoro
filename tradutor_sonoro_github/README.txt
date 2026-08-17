TRADUTOR SONORO v0.7
====================

MODO DE TRADUÇÃO AO VIVO
------------------------

A principal opção é:

3 - TRADUÇÃO AO VIVO

O programa deixa o microfone aberto continuamente.

FLUXO
-----

microfone
   |
   v
blocos de 50 ms
   |
   v
detecção de atividade
   |
   +--> silêncio: continua ouvindo
   |
   +--> som:
           |
           v
       acumula áudio
           |
           v
       previsão provisória
           |
           v
       fim do som
           |
           v
       reconhecimento final
           |
           v
       adiciona palavra à frase


PREVISÃO PROVISÓRIA
-------------------

Enquanto uma unidade sonora ainda está acontecendo, a tela pode mostrar:

🎤 "eu quero" [água? 71%]

Quando o som termina e a decisão é confirmada:

✓ água (78.3%)

🎤 "eu quero água"


FINALIZAÇÃO DA FRASE
--------------------

Se não houver novas palavras por aproximadamente 1,3 segundo:

FRASE AO VIVO:
eu quero água

Confiança média: 81.2%

Depois o programa continua ouvindo uma nova frase.


CALIBRAÇÃO
----------

Quando o modo ao vivo é iniciado, fique em silêncio durante cerca
de 1,5 segundo.

O programa usa esse período para medir o ruído ambiente.

Se houver muito ruído durante a calibração, a detecção poderá ficar ruim.


COMO TESTAR
-----------

Treine pelo menos 5 a 10 amostras de cada palavra.

Exemplo:

eu
quero
água
comida
amigo

Depois:

3 - TRADUÇÃO AO VIVO

Fique em silêncio durante a calibração.

Produza:

SOM_EU
pequena pausa
SOM_QUERO
pequena pausa
SOM_AGUA

A frase deve surgir progressivamente.


IMPORTANTE
----------

A v0.7 é "quase tempo real".

Ela não envia cada amostra do microfone diretamente ao DTW.
Isso seria muito pesado.

Em vez disso:

- o microfone recebe blocos de 50 ms;
- o detector de atividade identifica quando existe um evento;
- uma previsão provisória é feita periodicamente;
- a palavra é confirmada quando o evento termina.

Isso reduz uso de CPU e evita repetir a mesma palavra dezenas de vezes.


MIGRAÇÃO DA v0.6
----------------

Copie para a pasta da v0.7:

dicionario.db
audios/

O banco permanece compatível.


INSTALAÇÃO
----------

sudo apt update

sudo apt install -y \
  python3 \
  python3-venv \
  python3-pip \
  libportaudio2 \
  portaudio19-dev

python3 -m venv .venv

source .venv/bin/activate

pip install -r requirements.txt

python app.py


SAIR DO MODO AO VIVO
--------------------

Pressione:

Ctrl+C

Isso encerra apenas o modo ao vivo e retorna ao menu.
