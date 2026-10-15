# Build from the repository root:
#   docker build -f integrations/aml-cycle2/deploy/Dockerfile -t agent-memory-aml .
# Behind a TLS-intercepting proxy, pass its CA as a build secret (never stored in a layer):
#   docker build --secret id=extra_ca,src=/path/to/ca.pem -f ... .
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /src
COPY pyproject.toml setup.py README.md LICENSE NOTICE MANIFEST.in ./
COPY schemas ./schemas
COPY reference ./reference
COPY integrations/aml-cycle2 ./integrations/aml-cycle2
RUN --mount=type=secret,id=extra_ca,required=false \
    if [ -s /run/secrets/extra_ca ]; then export PIP_CERT=/run/secrets/extra_ca; fi \
    && pip install --no-cache-dir . ./integrations/aml-cycle2 \
    && useradd --system --uid 10001 --home-dir /data aml \
    && mkdir -p /data && chown aml /data
USER aml
VOLUME ["/data"]
EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=5s CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8080/health', timeout=4)"
# The key comes from AML_MEMORY_KEY or a mounted secret file (--key-file); the service refuses to start without one.
ENTRYPOINT ["agent-memory-aml", "--host", "0.0.0.0", "--port", "8080", "--data-dir", "/data"]
