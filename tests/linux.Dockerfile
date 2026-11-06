FROM python:3.12-slim
RUN apt-get update && apt-get install -y --no-install-recommends git unzip libgl1 libegl1 libglib2.0-0 && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir mujoco==3.10.0 numpy==2.4.1 Pillow==12.2.0
WORKDIR /src
COPY bridge/ bridge/
COPY tests/ tests/
COPY scripts/ scripts/
COPY packaging/ packaging/
COPY upstream-revisions.json README*.md ./
COPY docs/INSTALL.*.md docs/how-to.html docs/
ENV PYTHONDONTWRITEBYTECODE=1
CMD ["python", "-m", "unittest", "discover", "-s", "tests", "-v"]
