#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
HOME_DIR="$1"
COPY_DIR="$SCRIPT_DIR"/../mod/bin
IMAGE_TAG="${IMAGE_TAG:-orvibo-gynoid-zigbee-hub-sdk}"

shift
if [[ $# -lt 1 ]]; then
    DOCKER_COMMAND=( docker )
else
    DOCKER_COMMAND=( "$@" )
fi

dockerf () {
    "${DOCKER_COMMAND[@]}" "$@"
}

dockerf build -t "$IMAGE_TAG" "$SCRIPT_DIR"
dockerf run --rm \
    -v "$SCRIPT_DIR":/build_scripts/:ro \
    -v "$COPY_DIR":/build \
    "$IMAGE_TAG" \
    /build_scripts/dropbear.sh \
        /build/dropbearmulti \
        "$HOME_DIR"
dockerf run --rm \
    -v "$SCRIPT_DIR":/build_scripts/:ro \
    -v "$COPY_DIR":/build \
    "$IMAGE_TAG" \
    /build_scripts/serialgateway.sh \
        /build/serialgateway
