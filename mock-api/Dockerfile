FROM docker-remote.registry.saas.cagip.group.gca/python:3.12-slim
WORKDIR /app
COPY requirements.txt .
# Définir les variables d'environnement pour pip
ENV PIP_INDEX_URL=https://registry.saas.cagip.group.gca/artifactory/api/pypi/pypi-remote/simple
ENV PIP_TRUSTED_HOST=registry.saas.cagip.group.gca
RUN pip install --no-cache-dir -r requirements.txt
COPY *.py .
EXPOSE 8080
CMD ["uvicorn", "governance_app:app", "--host", "0.0.0.0", "--port", "8080"]
