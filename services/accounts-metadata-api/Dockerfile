# Build from the accounts repository root: docker build -f services/accounts-metadata-api/Dockerfile -t solo-accounts-metadata-api .
# Only the files declared in service.yaml data.reads are baked in; nothing else from the repo.
FROM python:3.12-slim
COPY --from=ghcr.io/astral-sh/uv:0.13.1 /uv /usr/local/bin/uv

# Dependencies come from uv.lock (--frozen), so every build installs the versions CI tested; the
# vendored service-auth is a path source in that lock, so it sits at the same relative path as in the repo.
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 ACCOUNTS_API_HOST=0.0.0.0 ACCOUNTS_API_ENV=production \
    UV_LINK_MODE=copy UV_PYTHON_DOWNLOADS=never \
    UV_PROJECT_ENVIRONMENT=/opt/venv PATH=/opt/venv/bin:$PATH
WORKDIR /app
COPY services/accounts-metadata-api/vendor/service-auth /app/services/accounts-metadata-api/vendor/service-auth
COPY services/accounts-metadata-api/pyproject.toml services/accounts-metadata-api/uv.lock services/accounts-metadata-api/server.py services/accounts-metadata-api/_sentry.py /app/services/accounts-metadata-api/
RUN uv sync --project /app/services/accounts-metadata-api --frozen --no-dev --no-editable --no-cache --python /usr/local/bin/python3
COPY accounts/ACCOUNT-MATRIX.yaml /app/accounts/ACCOUNT-MATRIX.yaml

RUN useradd --system --uid 10001 app
USER app
EXPOSE 3470
HEALTHCHECK --interval=15s --timeout=3s --retries=3 CMD python -c "import os, urllib.request; port=os.environ.get('ACCOUNTS_API_PORT', os.environ.get('PORT', '3470')); urllib.request.urlopen('http://127.0.0.1:'+port+'/ready', timeout=2)"
CMD ["python", "/app/services/accounts-metadata-api/server.py"]
