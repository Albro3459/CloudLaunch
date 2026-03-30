#!/bin/bash

set -euo pipefail

usage() {
    echo "Usage: ./build_layer.sh <base|oci> [zip_name]"
    echo "Example: ./build_layer.sh base"
    echo "Example: ./build_layer.sh oci oci-layer.zip"
}

# Check if Docker is running
if ! docker info >/dev/null 2>&1; then
    echo "ERROR: Docker is not running. Try again."
    exit 1
fi

if [ $# -lt 1 ]; then
    echo "ERROR: You must specify which layer to build: base or oci."
    usage
    exit 1
fi

LAYER_TARGET="$1"
OUTPUT_DIR="$HOME/Desktop"
ZIP_NAME="${2:-CloudLaunch-${LAYER_TARGET}-layer.zip}"

case "$LAYER_TARGET" in
    base)
        DOCKERFILE="Dockerfile"
        IMAGE_NAME="cloudlaunch-layer-image-base"
        CONTAINER_NAME="cloudlaunch-layer-container-base"
        ;;
    oci)
        DOCKERFILE="Dockerfile.oci"
        IMAGE_NAME="cloudlaunch-layer-image-oci"
        CONTAINER_NAME="cloudlaunch-layer-container-oci"
        ;;
    *)
        echo "ERROR: Invalid layer target '$LAYER_TARGET'. Use 'base' or 'oci'."
        usage
        exit 1
        ;;
esac

echo "Building $LAYER_TARGET layer with $DOCKERFILE..."
# PLATFORM IS IMPORTANT
docker build --platform linux/amd64 -f "$DOCKERFILE" -t "$IMAGE_NAME" .

echo "Creating Docker container..."
if docker ps -a --format '{{.Names}}' | grep -qx "$CONTAINER_NAME"; then
    docker rm "$CONTAINER_NAME" >/dev/null
fi
docker create --name "$CONTAINER_NAME" "$IMAGE_NAME"

echo "Copying /layer/python from container to $OUTPUT_DIR..."
mkdir -p "$OUTPUT_DIR"
docker cp $CONTAINER_NAME:/layer/python "$OUTPUT_DIR"

echo "Removing Docker container..."
docker rm "$CONTAINER_NAME"

echo "Zipping python folder to $ZIP_NAME..."
cd "$OUTPUT_DIR"
zip -r9 "$ZIP_NAME" python

echo "Cleaning up python folder..."
rm -rf "$OUTPUT_DIR"/python

echo "Done! Created $ZIP_NAME at $HOME/Desktop."
echo "PLATFORM: x86_64"
echo "RUNTIME: Python 3.11"
