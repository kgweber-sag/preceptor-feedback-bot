#!/bin/bash
set -e

echo "🚀 Deploying Preceptor Feedback Bot to Cloud Run..."

gcloud run deploy preceptor-feedback-bot \
  --source . \
  --region us-central1 \
  --project meded-gcp-sandbox \
  --timeout 600

echo "✅ Deployment complete!"
echo "🌐 View your app at the URL above"