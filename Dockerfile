FROM alpine:3.22

RUN apk add curl python3 exiftool
RUN adduser -D kakigoori

USER kakigoori

RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/home/kakigoori/.local/bin/:$PATH"

WORKDIR /kakigoori

COPY --chown=1000:1000 . .

RUN uv sync --group prod

ENTRYPOINT ["/home/kakigoori/.local/bin/uv", "run", "gunicorn"]
CMD ["-w", "4", "kakigoori.wsgi", "-b", "0.0.0.0:8001"]