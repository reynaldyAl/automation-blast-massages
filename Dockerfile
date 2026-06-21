# ─────────────────────────────────────────────────────────────────────────────
# Gunakan python:3.11-slim (~150MB) — jauh lebih ringan dari image Playwright (~1.3GB)
# Chromium diinstall via apt (bagian dari Ubuntu repos, lebih stabil downloadnya)
# ─────────────────────────────────────────────────────────────────────────────
FROM python:3.11-slim

LABEL maintainer="BPJS Kesehatan Kantor Cabang Serang"
LABEL description="BPJS Blast Message Automation — WA Web & SMS via ADB"

# ─── System Dependencies ──────────────────────────────────────────────────────
# Install Chromium dari apt (tidak perlu download terpisah via Playwright)
# + ADB untuk SMS via HP Android
RUN apt-get update && apt-get install -y --no-install-recommends \
    # Browser
    chromium \
    # ADB (untuk SMS)
    android-tools-adb \
    # Chromium runtime dependencies
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
    fonts-liberation \
    && rm -rf /var/lib/apt/lists/*

# ─── Beritahu Playwright pakai Chromium dari sistem (skip download browser) ───
ENV PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=1
ENV PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH=/usr/bin/chromium

# ─── Working Directory ────────────────────────────────────────────────────────
WORKDIR /app

# ─── Python Dependencies ──────────────────────────────────────────────────────
# Copy requirements dulu — manfaatkan layer cache
# Jika requirements.txt tidak berubah, layer ini tidak di-rebuild
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ─── Copy Project Files ───────────────────────────────────────────────────────
COPY src/ ./src/
COPY templates/ ./templates/
COPY .env.example ./.env.example

# ─── Buat direktori yang diperlukan ───────────────────────────────────────────
RUN mkdir -p data/reports screenshots wa_profile

# ─── Volume ──────────────────────────────────────────────────────────────────
VOLUME ["/app/data", "/app/wa_profile", "/app/screenshots"]

# ─── Environment ─────────────────────────────────────────────────────────────
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app/src

# ─── Entry Point ──────────────────────────────────────────────────────────────
ENTRYPOINT ["python", "src/main.py"]
CMD ["--help"]
