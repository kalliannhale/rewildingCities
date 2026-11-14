# rewildingCities Dockerfile
# Built from environment.yml, the project's one declared environment, so the
# image matches every laptop that runs `mamba env create -f environment.yml`.
# AMD64 because the AWS Batch and Fargate job definitions target it.
FROM --platform=linux/amd64 docker.io/condaforge/miniforge3:26.9.4-2

LABEL maintainer="rewildingCities"
LABEL description="Polyglot container for climate resilience research"

# ============================================
# Python + R environment (conda-forge, one GDAL/GEOS/PROJ for both)
# ============================================
COPY environment.yml /tmp/environment.yml
RUN mamba env create --yes --name rewilding --file /tmp/environment.yml \
    && mamba clean --all --yes \
    && rm /tmp/environment.yml

# Primitives call `Rscript` and `python` from PATH, so the env must come first.
ENV PATH=/opt/conda/envs/rewilding/bin:$PATH \
    PYTHONUNBUFFERED=1 \
    REWILDING_ROOT=/app

# ============================================
# Install {rewildr} R package from local source
# ============================================
COPY seeds/packages/rewildr /tmp/rewildr
RUN R CMD INSTALL /tmp/rewildr && rm -rf /tmp/rewildr

# ============================================
# Copy the codebase (.dockerignore keeps data, state and secrets out)
# ============================================
RUN useradd --create-home --uid 1000 rewilding
WORKDIR /app
COPY --chown=rewilding:rewilding . /app
USER rewilding

# ============================================
# Default: drop into bash (override with command)
# ============================================
CMD ["/bin/bash"]
