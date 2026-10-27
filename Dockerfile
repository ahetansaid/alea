# Image de démonstration pour Hugging Face Spaces (SDK Docker).
FROM python:3.12-slim

# Spaces exécute le conteneur avec l'utilisateur 1000
RUN useradd -m -u 1000 user
USER user
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH \
    HF_HOME=/home/user/.cache/huggingface \
    ALEA_ENABLE_LLM=0 \
    PYTHONUNBUFFERED=1
WORKDIR $HOME/app

# PyTorch version processeur : bien plus léger que la version par défaut
RUN pip install --no-cache-dir --user torch==2.14.1 --index-url https://download.pytorch.org/whl/cpu
COPY --chown=user requirements-space.txt .
RUN pip install --no-cache-dir --user -r requirements-space.txt

# Modèle d'embeddings téléchargé à la construction : pas d'attente au premier lancement
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2')"

COPY --chown=user . .
RUN test -f data/samples/portefeuille_gamma.csv || python scripts/generate_data.py

EXPOSE 8501
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0", "--server.headless=true", \
     "--server.enableXsrfProtection=false", "--browser.gatherUsageStats=false"]
