FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ src/
COPY alembic.ini .
COPY alembic/ alembic/

# W7-5 Release Identity: bakes the commit that produced this image so the
# running instance can identify itself (exposed at GET /health) without
# guessing from deploy logs. No new versioning system -- reuses Git.
ARG GIT_SHA=unknown
ENV RELEASE_SHA=${GIT_SHA}

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
