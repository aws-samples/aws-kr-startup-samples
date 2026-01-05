#!/bin/bash
set -e
cd "$(dirname "$0")/.."
npm run build
cd dist && zip -r ../dist.zip . && cd ..
echo "Created dist.zip"
