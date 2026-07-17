#!/bin/bash
# Deploy the ARD Registry stack (catalog + search service).
#
# Prerequisites:
#   - AWS CLI configured with credentials
#   - zip utility available
#
# Usage:
#   ./deploy.sh                          # uses defaults
#   ./deploy.sh my-bucket-name us-west-2 # custom bucket and region

set -e

STACK_NAME="ard-registry"
BUCKET_NAME="${1:-ard-registry-catalog-$(aws sts get-caller-identity --query Account --output text)}"
REGION="${2:-us-west-2}"

echo "Deploying ARD Registry"
echo "  Stack:  $STACK_NAME"
echo "  Bucket: $BUCKET_NAME"
echo "  Region: $REGION"
echo ""

# Step 1: Create S3 bucket (if it doesn't exist)
echo "[1/5] Creating S3 bucket..."
aws s3 mb "s3://$BUCKET_NAME" --region "$REGION" 2>/dev/null || true

# Step 2: Package and upload Lambda code + catalogs
echo "[2/5] Packaging and uploading artifacts..."
cd lambda
zip -q handler.zip handler.py
cd ..

aws s3 cp lambda/handler.zip "s3://$BUCKET_NAME/lambda/handler.zip" --region "$REGION"
aws s3 cp catalogs/partnerA.json "s3://$BUCKET_NAME/catalogs/partnerA.json" \
  --content-type application/json --region "$REGION"
aws s3 cp catalogs/partnerB.json "s3://$BUCKET_NAME/catalogs/partnerB.json" \
  --content-type application/json --region "$REGION"

# Step 3: Deploy CloudFormation stack
echo "[3/5] Deploying CloudFormation stack..."
aws cloudformation deploy \
  --stack-name "$STACK_NAME" \
  --template-file template.yaml \
  --parameter-overrides CatalogBucketName="$BUCKET_NAME" \
  --capabilities CAPABILITY_IAM \
  --region "$REGION" \
  --no-fail-on-empty-changeset

# Step 4: Wait for stack to complete
echo "[4/5] Waiting for stack..."
aws cloudformation wait stack-create-complete \
  --stack-name "$STACK_NAME" \
  --region "$REGION" 2>/dev/null || true

# Step 5: Print outputs
echo "[5/5] Done."
echo ""
echo "Stack outputs:"
aws cloudformation describe-stacks \
  --stack-name "$STACK_NAME" \
  --region "$REGION" \
  --query "Stacks[0].Outputs[*].[OutputKey,OutputValue]" \
  --output table

echo ""
echo "Test it:"
REGISTRY_URL=$(aws cloudformation describe-stacks \
  --stack-name "$STACK_NAME" \
  --region "$REGION" \
  --query "Stacks[0].Outputs[?OutputKey=='RegistryUrl'].OutputValue" \
  --output text)

echo "  curl -s -X POST \"$REGISTRY_URL\" \\"
echo "    -H \"Content-Type: application/json\" \\"
echo "    -d '{\"query\":{\"text\":\"flight hotel booking\",\"filter\":{\"type\":[\"application/a2a-agent-card+json\"]}},\"pageSize\":5}'"
