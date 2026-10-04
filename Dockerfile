ARG PYTHON_IMAGE
ARG UV_IMAGE
FROM ${UV_IMAGE} AS uv_binary
FROM ${PYTHON_IMAGE} AS bootstrap
COPY --from=uv_binary /uv /usr/local/bin/uv
WORKDIR /workspace

FROM bootstrap AS development
ARG UV_PROJECT_ENVIRONMENT
ENV UV_PROJECT_ENVIRONMENT=${UV_PROJECT_ENVIRONMENT}
ENV PATH="${UV_PROJECT_ENVIRONMENT}/bin:${PATH}"
COPY pyproject.toml uv.lock ./
RUN uv sync --locked --group dev --no-install-project
COPY src ./src
RUN uv sync --locked --group dev
