# Tradutor Sonoro

Protótipo experimental de tradução de um vocabulário sonoro aprendido pelo usuário.

A versão atual, **v0.7**, permite:

- cadastrar sons e associá-los a palavras;
- treinar várias amostras da mesma palavra;
- reconhecer sons usando características acústicas e DTW;
- manter o microfone aberto em modo de tradução ao vivo;
- detectar automaticamente eventos sonoros;
- mostrar previsões provisórias;
- montar frases progressivamente;
- aproveitar contexto de frases já confirmadas.

## Arquitetura

```text
Microfone
   ↓
InputStream
   ↓
blocos de áudio
   ↓
detecção de atividade
   ↓
MFCC
   ↓
DTW
   ↓
contexto
   ↓
palavra / frase
```

## Requisitos

Ubuntu/Xubuntu:

```bash
sudo apt update
sudo apt install -y \
  python3 \
  python3-venv \
  python3-pip \
  libportaudio2 \
  portaudio19-dev
```

## Instalação

```bash
git clone URL_DO_REPOSITORIO
cd tradutor-sonoro

python3 -m venv .venv
source .venv/bin/activate

pip install -r requirements.txt
python app.py
```

Ou:

```bash
chmod +x instalar.sh
./instalar.sh
```

## Uso

No menu:

```text
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
```

Antes de usar o modo ao vivo, treine pelo menos 5 a 10 amostras de cada palavra.

## GitHub Pages

A pasta `docs/` contém o site estático do projeto.

No GitHub:

1. Abra **Settings**.
2. Clique em **Pages**.
3. Em **Source**, selecione **Deploy from a branch**.
4. Escolha a branch `main`.
5. Escolha a pasta `/docs`.
6. Clique em **Save**.

O GitHub Pages usa `docs/index.html` como entrada do site.

## Importante

O **GitHub Pages não executa o programa Python**. Ele hospeda o site do projeto.  
O tradutor v0.7 continua sendo executado localmente no computador porque utiliza Python, PortAudio e acesso direto ao microfone.

Uma futura versão web poderá portar o reconhecimento para JavaScript/Web Audio API ou usar um backend.

## Privacidade

O banco `dicionario.db` e os arquivos WAV de treinamento estão ignorados pelo Git por padrão. Isso evita publicar acidentalmente dados de áudio pessoais.

## Estado do projeto

Projeto experimental em desenvolvimento. A confiança apresentada pelo reconhecedor é uma medida de similaridade do protótipo, não uma probabilidade estatística.
