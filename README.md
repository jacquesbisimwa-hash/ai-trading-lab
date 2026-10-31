# AI Trading Lab — prototype éducatif

## Contenu
- `app.py` : application Streamlit de démonstration.
- `requirements.txt` : dépendances Python.

## Important
Ce prototype utilise uniquement des prix synthétiques générés localement.
Il ne se connecte à aucune plateforme, ne collecte aucun prix réel et ne passe aucun ordre.
Les indicateurs et observations sont pédagogiques et ne constituent pas des conseils financiers.

## Lancer localement
```bash
python -m venv .venv
# Windows PowerShell:
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
streamlit run app.py
```

## Déploiement cloud
Le déploiement peut se faire via Streamlit Community Cloud en reliant un dépôt GitHub contenant ces fichiers, puis en choisissant `app.py` comme fichier principal.
Ne placez jamais de mot de passe, clé privée ou secret personnel dans le code.
