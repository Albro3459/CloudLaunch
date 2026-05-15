#!/usr/bin/env bash

# Bundles the needed terraform files into the output package for the Deploy lambda

set -euo pipefail

script_dir="$(cd -- "$(dirname -- "$0")" && pwd)"
repo_root="$(cd -- "$script_dir/../.." && pwd)"

output_dir="${CLOUDLAUNCH_PUBLISH_OUTPUT_DIR:-$HOME/Desktop/CloudLaunch-Publish}"
terraform_output_dir="$output_dir/terraform"

if [ -e "$output_dir" ]; then
  trash "$output_dir"
fi

mkdir -p "$output_dir"

while IFS= read -r source_path; do
  relative_path="${source_path#$script_dir/}"
  target_path="$output_dir/$relative_path"

  if [ -d "$source_path" ]; then
    mkdir -p "$target_path"
  else
    mkdir -p "$(dirname "$target_path")"
    cp "$source_path" "$target_path"
  fi
done < <(
  find "$script_dir" -mindepth 1 \
    ! -name ".DS_Store" \
    ! -path "$script_dir/build_deploy_lambda.sh" \
    ! -path "$script_dir/terraform" \
    ! -path "$script_dir/terraform/*" \
    ! -path "*/__pycache__/*" \
    ! -path "*/.pytest_cache/*" \
    ! -path "*/.venv/*" \
    ! -path "*/venv/*"
)

mkdir -p "$terraform_output_dir"
cp "$repo_root/OCI/terraform/cloudlaunch.tf" "$terraform_output_dir/"
cp "$repo_root/OCI/terraform/wireguard-cloud-init.sh.tftpl" "$terraform_output_dir/"
cp "$repo_root/OCI/terraform/backdoor-cloud-init.yaml" "$terraform_output_dir/"

echo "Deploy Lambda package prepared at $output_dir"
