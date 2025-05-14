FROM alpine:3.21

RUN apk add curl python3 exiftool
RUN adduser -D kakigoori

USER kakigoori

RUN curl -LsSf https://astral.sh/uv/install.sh | sh

WORKDIR /kakigoori

COPY . .

RUN /home/kakigoori/.local/bin/uv sync

ENTRYPOINT ["/home/kakigoori/.local/bin/uv", "run", "gunicorn"]
CMD ["-w", "4", "kakigoori.wsgi", "-b", "0.0.0.0:8001"]