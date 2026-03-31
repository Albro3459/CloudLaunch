#!/bin/bash

set -euo pipefail

OUTPUT_DIR="$HOME/Desktop"
ZIP_NAME="${2:-CloudLaunch-layer.zip}"
DOCKERFILE="Dockerfile"
IMAGE_NAME="cloudlaunch-layer-image"
CONTAINER_NAME="cloudlaunch-layer-container"

echo "Building $ZIP_NAME layer with $DOCKERFILE..."
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
