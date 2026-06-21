# ─── Base Image ───────────────────────────────────────────────────────────────
# Gunakan Python 3.11 slim sebagai base
FROM python:3.11-slim

# Label
LABEL maintainer="BPJS Kesehatan Kantor Cabang Serang"
LABEL description="BPJS Blast Message Automation — WA Web & SMS via ADB"

# ─── System Dependencies ──────────────────────────────────────────────────────
RUN apt-get update && apt-get install -y \
    # Playwright Chromium dependencies
    libnss3 \
    libnspr4 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libasound2 \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    # ADB
    android-tools-adb \
    # Utilities
    curl \
    && rm -rf /var/lib/apt/lists/*

# ─── Working Directory ────────────────────────────────────────────────────────
WORKDIR /app

# ─── Python Dependencies ──────────────────────────────────────────────────────
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright dan download browser Chromium
RUN playwright install chromium
RUN playwright install-deps chromium

# ─── Copy Project Files ───────────────────────────────────────────────────────
COPY src/ ./src/
COPY templates/ ./templates/
COPY .env.example ./.env.example

# ─── Buat direktori yang diperlukan ───────────────────────────────────────────
RUN mkdir -p data/reports screenshots wa_profile

# ─── Volume: data & output ────────────────────────────────────────────────────
# Mount data/ dari host agar bisa ganti CSV tanpa rebuild image
VOLUME ["/app/data", "/app/wa_profile", "/app/screenshots"]

# ─── Environment Defaults ─────────────────────────────────────────────────────
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app/src

# ─── Entry Point ──────────────────────────────────────────────────────────────
ENTRYPOINT ["python", "src/main.py"]
CMD ["--help"]
