# Publicar no GitHub e GitHub Pages

## 1. Criar o repositório

No GitHub, crie um novo repositório chamado, por exemplo:

`tradutor-sonoro`

Não marque a opção para criar README, `.gitignore` ou licença, pois estes arquivos já estão nesta pasta.

## 2. Enviar pelo terminal

Dentro desta pasta:

```bash
git init
git branch -M main
git add .
git commit -m "Publica Tradutor Sonoro v0.7"
git remote add origin https://github.com/SEU_USUARIO/tradutor-sonoro.git
git push -u origin main
```

Se o Git pedir identidade:

```bash
git config --global user.name "Seu Nome"
git config --global user.email "seu-email@example.com"
```

## 3. Ativar GitHub Pages

No repositório:

- Settings
- Pages
- Source: Deploy from a branch
- Branch: main
- Folder: /docs
- Save

O site deverá ficar no formato:

`https://SEU_USUARIO.github.io/tradutor-sonoro/`

## 4. Atualizações futuras

```bash
git add .
git commit -m "Descrição da atualização"
git push
```

Qualquer alteração em `docs/` será republicada pelo Pages.
