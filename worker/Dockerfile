FROM rust:1.95.0-alpine3.23 AS builder

RUN apk add musl-dev

WORKDIR /kakigooriworker

COPY . .
RUN cargo build --release

FROM cgr.dev/chainguard/static:latest
WORKDIR /kakigoori

COPY --from=builder /kakigooriworker/target/release/kakigoori-worker .
COPY --from=git.prettysunflower.moe/prettysunflower/webp:libwebp-1.6.0-2 /usr/bin/cwebp /usr/bin/
COPY --from=git.prettysunflower.moe/prettysunflower/avif:libavif-1.4.1-libaom-3.13.3-svta1psyex-3.0.2B /usr/bin/avifenc /usr/bin/

CMD ["/kakigoori/kakigoori-worker"]
