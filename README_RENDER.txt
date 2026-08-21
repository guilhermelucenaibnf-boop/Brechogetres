BRECHÓ GETRES — arquivos para Render

Envie para o GitHub:
- app.py
- requirements.txt
- render.yaml
- .gitignore

No Render, conecte o repositório.
O render.yaml já define:
Build: pip install -r requirements.txt
Start: gunicorn app:app --bind 0.0.0.0:$PORT

IMPORTANTE:
O app atual usa SQLite (brechog3.db) e salva fotos em static/produtos.
Em hospedagem, banco e uploads locais precisam de armazenamento persistente
para não serem perdidos em recriações/redeploys do serviço.
