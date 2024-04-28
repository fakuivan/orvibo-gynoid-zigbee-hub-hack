#!/usr/bin/env bash
set -euo pipefail
COPY_PATH="$1"
quote_c () {
    printf "%s" "$1" | jq -RsaM
}

. /sdk/*-activate
ln -s mips-linux-uclibc-gcc-4.4.7 /sdk/bin/mips-linux-uclibc-gcc

git clone https://github.com/fakuivan/lidl-gateway-freedom.git /program
cd /program/gateway
git checkout 'Release-1.4'
GIT_VERSION="$(git describe --all --long --dirty --always)"

mips-linux-gcc \
    -static \
    main.c serial.c \
    -o "$COPY_PATH" \
    -DVERSION="$(quote_c "$GIT_VERSION")"