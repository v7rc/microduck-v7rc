FROM python:3.12-slim
RUN apt-get update && apt-get install -y --no-install-recommends git libgl1 libegl1 libglib2.0-0 && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir mujoco==3.10.0 numpy==2.4.1 Pillow==12.2.0
WORKDIR /src
COPY bridge/ bridge/
COPY tests/ tests/
COPY scripts/setup.py scripts/setup.py
ENV PYTHONDONTWRITEBYTECODE=1
CMD ["python", "-m", "unittest", "discover", "-s", "tests", "-v"]
