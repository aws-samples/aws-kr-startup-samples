#!/bin/bash
set -e

APP_NAME="${APP_NAME:-claude_code_proxy}"
BRANCH="${BRANCH:-main}"
REGION="${AWS_REGION:-ap-northeast-2}"
ZIP_PATH="${ZIP_PATH:-dist.zip}"

cd "$(dirname "$0")/.."

# Build if zip doesn't exist or SKIP_BUILD not set
if [[ "$SKIP_BUILD" != "1" ]]; then
  npm run build:zip
fi

[[ ! -f "$ZIP_PATH" ]] && echo "Error: $ZIP_PATH not found" && exit 1

# Find or create app
APP_ID=$(aws amplify list-apps --region "$REGION" --query "apps[?name=='$APP_NAME'].appId | [0]" --output text 2>/dev/null || echo "None")

if [[ "$APP_ID" == "None" || -z "$APP_ID" ]]; then
  echo "Creating new Amplify app: $APP_NAME"
  APP_ID=$(aws amplify create-app --name "$APP_NAME" --region "$REGION" --query 'app.appId' --output text)
  
  # Add SPA rewrite rule (exclude static assets)
  aws amplify update-app --app-id "$APP_ID" --region "$REGION" \
    --custom-rules '[{"source":"</^[^.]+$|\\.(?!(js|css|ico|png|jpg|jpeg|gif|svg|woff|woff2|ttf|eot|json|map)$)([^.]+$)/>","target":"/index.html","status":"200"}]' >/dev/null
  
  # Create branch
  aws amplify create-branch --app-id "$APP_ID" --branch-name "$BRANCH" --region "$REGION" >/dev/null
  echo "Created app $APP_ID with branch $BRANCH"
else
  echo "Using existing app: $APP_ID"
  # Ensure branch exists
  if ! aws amplify get-branch --app-id "$APP_ID" --branch-name "$BRANCH" --region "$REGION" >/dev/null 2>&1; then
    aws amplify create-branch --app-id "$APP_ID" --branch-name "$BRANCH" --region "$REGION" >/dev/null
    echo "Created branch $BRANCH"
  fi
fi

# Deploy
DEPLOYMENT=$(aws amplify create-deployment --app-id "$APP_ID" --branch-name "$BRANCH" --region "$REGION")
JOB_ID=$(echo "$DEPLOYMENT" | grep -o '"jobId"[[:space:]]*:[[:space:]]*"[^"]*"' | cut -d'"' -f4)
UPLOAD_URL=$(echo "$DEPLOYMENT" | grep -o '"zipUploadUrl"[[:space:]]*:[[:space:]]*"[^"]*"' | cut -d'"' -f4)

curl -s -H "Content-Type: application/zip" --upload-file "$ZIP_PATH" "$UPLOAD_URL" >/dev/null
aws amplify start-deployment --app-id "$APP_ID" --branch-name "$BRANCH" --job-id "$JOB_ID" --region "$REGION" >/dev/null

echo "Deployment started: https://$BRANCH.$APP_ID.amplifyapp.com"
