FROM alpine:3.22

COPY --from=git.prettysunflower.moe/prettysunflower/avif:libavif-1.3.0-libaom-3.13.1-svtav1psyex-3.0.2B /usr/bin/avifenc /usr/bin/avifenc

RUN apk add curl libwebp libwebp-tools
RUN adduser -D kakigoori
RUN mkdir /kakigoori
RUN chown kakigoori:kakigoori /kakigoori

USER kakigoori

RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/home/kakigoori/.local/bin/:$PATH"

WORKDIR /kakigoori

COPY main.py .
COPY pyproject.toml .

RUN uv sync

ENV PYTHONUNBUFFERED=1

CMD ["uv", "run", "main.py"]