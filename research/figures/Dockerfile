FROM python:3.10-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    MPLCONFIGDIR=/tmp/matplotlib

WORKDIR /workspace

RUN apt-get update \
    && apt-get install -y --no-install-recommends fonts-noto-cjk \
    && rm -rf /var/lib/apt/lists/*

COPY research/figures/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

COPY research/figures /workspace/research/figures
COPY data/releases/2026.08.3_federated /workspace/data/releases/2026.08.3_federated

CMD ["/bin/sh", "-c", "python research/figures/generate_figures.py && python research/figures/generate_extended_figures.py && python research/figures/build_delivery_package.py"]
