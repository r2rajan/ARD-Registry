#!/bin/bash
# Deploy the improved scoring Lambda (stop words + stemming + vector embeddings)
# to the existing ARD Registry stack from Part 2.
#
# This script:
# 1. Adds Bedrock InvokeModel permission to the Lambda role
# 2. Updates the Lambda function code
# 3. Increases Lambda timeout (embeddings take a few seconds on cold start)
#
# Prerequisites:
#   - Part 2 stack already deployed (ard-registry)
#   - AWS CLI configured with credentials
#   - Bedrock Titan Embed Text v2 model access enabled in us-west-2
#
# Usage:
#   ./deploy.sh                          # uses defaults
#   ./deploy.sh my-bucket-name us-west-2 # custom bucket and region

set -e

STACK_NAME="ard-registry"
BUCKET_NAME="${1:-ard-registry-catalog-$(aws sts get-caller-identity --query Account --output text)}"
REGION="${2:-us-west-2}"

echo "Deploying improved scoring Lambda (keyword + vector embeddings)"
echo "  Stack:  $STACK_NAME"
echo "  Bucket: $BUCKET_NAME"
echo "  Region: $REGION"
echo ""

# Step 1: Package the improved Lambda
echo "[1/4] Packaging Lambda code..."
cd lambda
zip -q handler.zip handler.py
cd ..

# Step 2: Upload to S3
echo "[2/4] Uploading to S3..."
aws s3 cp lambda/handler.zip "s3://$BUCKET_NAME/lambda/handler.zip" --region "$REGION"

# Step 3: Get Lambda function name and role
FUNCTION_NAME=$(aws cloudformation describe-stack-resource \
  --stack-name "$STACK_NAME" \
  --logical-resource-id RegistryFunction \
  --region "$REGION" \
  --query "StackResourceDetail.PhysicalResourceId" \
  --output text)

ROLE_ARN=$(aws lambda get-function-configuration \
  --function-name "$FUNCTION_NAME" \
  --region "$REGION" \
  --query "Role" \
  --output text)

ROLE_NAME=$(echo "$ROLE_ARN" | awk -F'/' '{print $NF}')

# Add Bedrock permissions to the role (idempotent)
echo "[3/4] Adding Bedrock permissions and updating Lambda..."

POLICY_DOC='{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": "bedrock:InvokeModel",
      "Resource": "arn:aws:bedrock:*::foundation-model/amazon.titan-embed-text-v2:0"
    }
  ]
}'

aws iam put-role-policy \
  --role-name "$ROLE_NAME" \
  --policy-name BedrockEmbeddings \
  --policy-document "$POLICY_DOC" 2>/dev/null || true

# Update Lambda code and increase timeout for embedding cold start
aws lambda update-function-code \
  --function-name "$FUNCTION_NAME" \
  --s3-bucket "$BUCKET_NAME" \
  --s3-key lambda/handler.zip \
  --region "$REGION" \
  --no-cli-pager > /dev/null

# Wait for update to complete
aws lambda wait function-updated --function-name "$FUNCTION_NAME" --region "$REGION"

# Increase timeout to 60s (embeddings on cold start take time)
aws lambda update-function-configuration \
  --function-name "$FUNCTION_NAME" \
  --timeout 60 \
  --memory-size 512 \
  --region "$REGION" \
  --no-cli-pager > /dev/null

# Step 4: Print test commands
echo "[4/4] Done."
echo ""

REGISTRY_URL=$(aws cloudformation describe-stacks \
  --stack-name "$STACK_NAME" \
  --region "$REGION" \
  --query "Stacks[0].Outputs[?OutputKey=='RegistryUrl'].OutputValue" \
  --output text)

echo "Registry URL: $REGISTRY_URL"
echo ""
echo "Test (now returns both keywordScore and vectorScore):"
echo ""
echo "  curl -s -X POST \"$REGISTRY_URL\" \\"
echo "    -H \"Content-Type: application/json\" \\"
echo "    -d '{\"query\":{\"text\":\"I need to pay for my trip\"},\"pageSize\":3}' | python3 -m json.tool"
