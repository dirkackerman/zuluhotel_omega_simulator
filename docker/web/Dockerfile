# Omega Combat Simulator — Streamlit Web UI
#
# TODO: Update base image to ubuntu:26.04 when released from preview.
#       Currently pinned to 25.04 (plucky) as 26.04 is not yet GA.
#       Track: https://releases.ubuntu.com/
#
# Build:  docker/web/build.sh
# Run:    docker run -d -p 8501:8501 -v ./submodules/zuluhotel_omega_2.5:/shard:ro zh_sim

FROM ubuntu:resolute-20260108

LABEL maintainer="zuluhotel-omega"
LABEL description="Omega Combat Simulator — Streamlit Web UI"

# Avoid interactive prompts during package install
ENV DEBIAN_FRONTEND=noninteractive

# --------------------------------------------------------------------------
# System packages — Python 3.14 + minimal build deps
# --------------------------------------------------------------------------

RUN apt-get update && apt-get install -y --no-install-recommends \
        python3.14 \
        python3.14-venv \
        python3-pip \
        ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# --------------------------------------------------------------------------
# Application setup
# --------------------------------------------------------------------------

WORKDIR /app

# Create venv with python3.14
RUN python3.14 -m venv /app/.venv
ENV PATH="/app/.venv/bin:$PATH"
ENV VIRTUAL_ENV="/app/.venv"

# Install Python dependencies first (cache-friendly layer)
COPY pyproject.toml /app/
COPY src/ /app/src/

RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir \
        . \
        streamlit>=1.55.0 \
        plotly>=6.6.0 \
        pyyaml>=6.0

# Copy the web app
COPY notebooks/web/ /app/notebooks/web/

# --------------------------------------------------------------------------
# Shard mount point — the only external dependency
# --------------------------------------------------------------------------

# The shard files are mounted at runtime via -v, not baked in.
# This makes shard changes immediate with no rebuild required.
VOLUME ["/shard"]

# --------------------------------------------------------------------------
# Streamlit configuration
# --------------------------------------------------------------------------

# Disable telemetry, file watcher (we want shard changes live, not app restarts),
# and the browser auto-open
RUN mkdir -p /root/.streamlit && cat > /root/.streamlit/config.toml <<'EOF'
[server]
port = 8501
address = "0.0.0.0"
headless = true
fileWatcherType = "none"
maxUploadSize = 10

[browser]
gatherUsageStats = false

[theme]
base = "dark"
EOF

EXPOSE 8501

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8501/_stcore/health')" || exit 1

# --------------------------------------------------------------------------
# Entrypoint
# --------------------------------------------------------------------------

CMD ["streamlit", "run", "notebooks/web/app.py"]
