#!/bin/bash

# How to Run: ./build_layer.sh `file_name`

# Check if Docker is running
if ! docker info >/dev/null 2>&1; then
    echo "ERROR: Docker is not running. Try again."
    exit 1
fi

OUTPUT_DIR="$HOME/Desktop"
CONTAINER_NAME="layer-builder-container"
IMAGE_NAME="layer-builder-image"
ZIP_NAME="${1:-layer.zip}"  # defaults to layer.zip if no argument

echo "Building Docker image..."
# PLATFORM IS IMPORTANT
docker build --platform linux/amd64 -t "$IMAGE_NAME" .

echo "Creating Docker container..."
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

echo "Done! Created "$ZIP_NAME"at $HOME/Desktop."
