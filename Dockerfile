# rewildingCities Dockerfile
# Force AMD64 for AWS compatibility
FROM --platform=linux/amd64 rocker/geospatial:4.3

LABEL maintainer="rewildingCities"
LABEL description="Polyglot container for climate resilience research"

# ============================================
# System dependencies + Python
# ============================================
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 \
    python3-pip \
    python3-venv \
    && rm -rf /var/lib/apt/lists/*

# Symlink python -> python3 for convenience
RUN ln -s /usr/bin/python3 /usr/bin/python

# ============================================
# Python dependencies
# ============================================
COPY requirements.txt /tmp/requirements.txt
RUN pip3 install --no-cache-dir -r /tmp/requirements.txt

# ============================================
# Install {rewildr} R package from local source
# ============================================
COPY seeds/packages/rewildr /tmp/rewildr
RUN R CMD INSTALL /tmp/rewildr && rm -rf /tmp/rewildr

# ============================================
# Copy the full codebase
# ============================================
WORKDIR /app
COPY . /app

# ============================================
# Default: drop into bash (override with command)
# ============================================
CMD ["/bin/bash"]