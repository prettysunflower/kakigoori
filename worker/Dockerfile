FROM alpine:3.22 AS avifbuilder

RUN apk add git cmake yasm clang20 clang20-dev alpine-sdk
RUN git clone -b v1.3.0 https://github.com/AOMediaCodec/libavif.git

WORKDIR /libavif/ext
RUN git clone -b v3.0.2-B https://github.com/BlueSwordM/svt-av1-psyex.git SVT-AV1

WORKDIR /libavif/ext/SVT-AV1/Build/linux
ENV CC=clang CXX=clang++
RUN ./build.sh --native --static --release --enable-lto --no-apps

WORKDIR /libavif/ext/SVT-AV1
RUN mkdir -p include/svt-av1
RUN cp Source/API/*.h include/svt-av1

WORKDIR /libavif
RUN cmake -S . -B build  \
    -DAVIF_CODEC_SVT=LOCAL  \
    -DAVIF_LIBYUV=LOCAL  \
    -DAVIF_LIBSHARPYUV=LOCAL  \
    -DAVIF_JPEG=LOCAL  \
    -DAVIF_ZLIBPNG=LOCAL  \
    -DAVIF_LIBXML2=LOCAL \
    -DAVIF_BUILD_APPS=ON  \
    -DBUILD_SHARED_LIBS=OFF
RUN cmake --build build --config Release --parallel

FROM alpine:3.22

COPY --from=avifbuilder /libavif/build/avifenc /usr/bin/avifenc

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