# Build from the accounts repository root: docker build -f services/accounts-metadata-api/Dockerfile -t solo-accounts-metadata-api .
# Only the files declared in service.yaml data.reads are baked in; nothing else from the repo.
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1 ACCOUNTS_API_HOST=0.0.0.0 ACCOUNTS_API_ENV=production
WORKDIR /app
COPY services/accounts-metadata-api/vendor/service-auth /app/vendor/service-auth
COPY services/accounts-metadata-api/pyproject.toml services/accounts-metadata-api/server.py services/accounts-metadata-api/_sentry.py /app/services/accounts-metadata-api/
RUN pip install /app/vendor/service-auth /app/services/accounts-metadata-api
COPY accounts/ACCOUNT-MATRIX.yaml /app/accounts/ACCOUNT-MATRIX.yaml

RUN useradd --system --uid 10001 app
USER app
EXPOSE 3470
HEALTHCHECK --interval=15s --timeout=3s --retries=3 CMD python -c "import os, urllib.request; port=os.environ.get('ACCOUNTS_API_PORT', os.environ.get('PORT', '3470')); urllib.request.urlopen('http://127.0.0.1:'+port+'/ready', timeout=2)"
CMD ["python", "/app/services/accounts-metadata-api/server.py"]
