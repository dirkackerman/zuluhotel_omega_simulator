#!/usr/bin/env bash
# Build (and optionally restart) the Omega Combat Simulator web container.
#
# Usage:
#   docker/web/build.sh          # build only
#   docker/web/build.sh -f       # stop + remove existing container, then build
#   docker/web/build.sh -f -r    # stop + remove, build, then run
#
# The script must be run from the repository root:
#   zuluhotel_omega_simulator$ docker/web/build.sh -f

set -euo pipefail

IMAGE_NAME="zh_sim"
CONTAINER_NAME="zh_sim"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

FORCE=false
RUN_AFTER=false

while getopts "fr" opt; do
    case $opt in
        f) FORCE=true ;;
        r) RUN_AFTER=true ;;
        *) echo "Usage: $0 [-f] [-r]" >&2; exit 1 ;;
    esac
done

cd "$REPO_ROOT"

# ── Stop and remove existing container if -f ──
if $FORCE; then
    if docker ps -q --filter "name=^${CONTAINER_NAME}$" | grep -q .; then
        echo "Stopping container '${CONTAINER_NAME}'..."
        docker stop "$CONTAINER_NAME"
    fi
    if docker ps -aq --filter "name=^${CONTAINER_NAME}$" | grep -q .; then
        echo "Removing container '${CONTAINER_NAME}'..."
        docker rm "$CONTAINER_NAME"
    fi
fi

# ── Build ──
echo "Building image '${IMAGE_NAME}'..."
docker build \
    -t "$IMAGE_NAME" \
    -f docker/web/Dockerfile \
    .

echo ""
echo "Build complete: ${IMAGE_NAME}"
echo ""

# ── Run if requested ──
if $RUN_AFTER; then
    echo "Starting container '${CONTAINER_NAME}'..."
    docker run -d \
        --name "$CONTAINER_NAME" \
        -p 8501:8501 \
        -v "$(pwd)/submodules/zuluhotel_omega_2.5:/shard:ro" \
        "$IMAGE_NAME"
    echo "Running at http://localhost:8501"
else
    echo "Run with:"
    echo "  docker run -d -p 8501:8501 -v \$(pwd)/submodules/zuluhotel_omega_2.5:/shard:ro ${IMAGE_NAME}"
fi
