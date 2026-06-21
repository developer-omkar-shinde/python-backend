#!/usr/bin/env bash
# Builds the onboarding event-consumer Lambda deployment zip.
#
# The handler is `onboarding.lambda_function.lambda_handler`, so the zip must
# contain the `onboarding` and `helper` packages at its root. The consumer path
# (lambda_function -> handler -> registry -> helper.utilities) is pure stdlib,
# and boto3 already ships in the Lambda runtime, so no third-party deps are
# bundled. If a handler later needs a non-runtime package (e.g. pydantic),
# install it into "$BUILD_DIR" on a Linux runner before zipping.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BUILD_DIR="$ROOT/dist/onboarding-build"
ZIP_PATH="$ROOT/dist/onboarding-lambda.zip"

rm -rf "$BUILD_DIR" "$ZIP_PATH"
mkdir -p "$BUILD_DIR"

cp -r "$ROOT/services/onboarding_service/onboarding" "$BUILD_DIR/onboarding"
cp -r "$ROOT/helper" "$BUILD_DIR/helper"

find "$BUILD_DIR" -type d -name '__pycache__' -prune -exec rm -rf {} +
find "$BUILD_DIR" -type f -name '*.pyc' -delete

(cd "$BUILD_DIR" && zip -qr "$ZIP_PATH" .)

echo "Built $ZIP_PATH"
