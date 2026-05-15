#!/usr/bin/env bash

# Zips and publishes the specified Lambda function to AWS

set -euo pipefail

AWS_PROFILE_NAME="cloudlaunch"
OUTPUT_ROOT="$HOME/Desktop/CloudLaunch-Publish"

script_dir="$(cd -- "$(dirname -- "$0")" && pwd)"

usage() {
  cat <<EOF
Usage:
  $(basename "$0") <lambda>

Options:
  Deploy
  CreateUser
  SecureGet
EOF
}

if [ "$#" -ne 1 ]; then
  usage
  exit 1
fi

requested_lambda="$(printf '%s' "$1" | tr '[:upper:]' '[:lower:]')"

case "$requested_lambda" in
  deploy)
    lambda_folder="Deploy"
    lambda_name="Deploy"
    ;;
  createuser)
    lambda_folder="CreateUser"
    lambda_name="CreateUser"
    ;;
  secureget)
    lambda_folder="SecureGet"
    lambda_name="SecureGet"
    ;;
  *)
    echo "Invalid lambda: $1"
    echo
    usage
    exit 1
    ;;
esac

lambda_dir="$script_dir/$lambda_folder"

if [ ! -d "$lambda_dir" ]; then
  echo "Lambda folder not found: $lambda_dir"
  exit 1
fi

stage_root="$OUTPUT_ROOT/stage"
package_root="$OUTPUT_ROOT/packages"

stage_dir="$stage_root/$lambda_name"
output_path="$package_root/$lambda_name.zip"

echo "Preparing Lambda: $lambda_name"
echo "Source folder: $lambda_dir"
echo "Stage folder: $stage_dir"
echo "Output zip: $output_path"
echo "AWS profile: $AWS_PROFILE_NAME"

if [ -e "$stage_dir" ]; then
  trash "$stage_dir"
fi
mkdir -p "$stage_dir" "$package_root"

if [ "$lambda_name" = "Deploy" ] && [ -f "$lambda_dir/build_deploy_lambda.sh" ]; then
  echo "Running Deploy package prep script"

  CLOUDLAUNCH_PUBLISH_OUTPUT_DIR="$stage_dir" bash "$lambda_dir/build_deploy_lambda.sh"
else
  echo "Copying Lambda source files"

  while IFS= read -r source_path; do
    relative_path="${source_path#$lambda_dir/}"
    target_path="$stage_dir/$relative_path"

    if [ -d "$source_path" ]; then
      mkdir -p "$target_path"
    else
      mkdir -p "$(dirname "$target_path")"
      cp "$source_path" "$target_path"
    fi
  done < <(
    find "$lambda_dir" -mindepth 1 \
      ! -name ".DS_Store" \
      ! -path "*/__pycache__/*" \
      ! -path "*/.pytest_cache/*" \
      ! -path "*/.venv/*" \
      ! -path "*/venv/*"
  )
fi

if [ -e "$output_path" ]; then
  trash "$output_path"
fi

echo "Zipping Lambda package"

(
  cd "$stage_dir"
  zip -r "$output_path" . \
    -x "*.DS_Store" \
    -x "__pycache__/*" \
    -x "*/__pycache__/*" \
    -x ".pytest_cache/*" \
    -x "*/.pytest_cache/*" \
    -x ".venv/*" \
    -x "*/.venv/*" \
    -x "venv/*" \
    -x "*/venv/*"
)

echo "Deploying to AWS Lambda function $lambda_name"

aws lambda update-function-code \
  --zip-file "fileb://$output_path" \
  --profile "$AWS_PROFILE_NAME" \
  --function-name "$lambda_name" \
  --architectures x86_64 \
  --no-paginate

echo "Deployment completed successfully"
