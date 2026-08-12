#!/bin/bash
# Deploy the ARD Travel Planner backend to ECS Fargate.
#
# Prerequisites:
#   - AWS CLI configured
#   - Docker running
#   - AgentCore agents already deployed (run deploy-agents.sh first)
#
# Usage:
#   ./deploy.sh

set -e

STACK_NAME="ard-travel-planner"
REGION="${AWS_REGION:-us-west-2}"
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
ECR_REPO="ard-travel-planner"
IMAGE_TAG="latest"
IMAGE_URI="${ACCOUNT_ID}.dkr.ecr.${REGION}.amazonaws.com/${ECR_REPO}:${IMAGE_TAG}"

# Agent ARNs
ORCHESTRATOR_ARN="arn:aws:bedrock-agentcore:${REGION}:${ACCOUNT_ID}:runtime/travelorchestrator_travel_orchestrator-233tROGGKt"
REGISTRY_URL="https://w6jdnh5xal.execute-api.us-west-2.amazonaws.com/search"

echo "Deploying ARD Travel Planner"
echo "  Stack:    $STACK_NAME"
echo "  Region:   $REGION"
echo "  Image:    $IMAGE_URI"
echo ""

# Step 1: Create ECR repo (if not exists)
echo "[1/4] Creating ECR repository..."
aws ecr describe-repositories --repository-names "$ECR_REPO" --region "$REGION" > /dev/null 2>&1 || \
  aws ecr create-repository --repository-name "$ECR_REPO" --region "$REGION" --no-cli-pager > /dev/null

# Step 2: Build and push Docker image
echo "[2/4] Building and pushing Docker image..."
aws ecr get-login-password --region "$REGION" | docker login --username AWS --password-stdin "${ACCOUNT_ID}.dkr.ecr.${REGION}.amazonaws.com"

docker build -t "$ECR_REPO" ../backend/
docker tag "$ECR_REPO:latest" "$IMAGE_URI"
docker push "$IMAGE_URI"

# Step 3: Deploy CloudFormation stack
echo "[3/4] Deploying CloudFormation stack..."
aws cloudformation deploy \
  --stack-name "$STACK_NAME" \
  --template-file template.yaml \
  --parameter-overrides \
    ImageUri="$IMAGE_URI" \
    OrchestratorArn="$ORCHESTRATOR_ARN" \
    RegistryUrl="$REGISTRY_URL" \
  --capabilities CAPABILITY_IAM \
  --region "$REGION" \
  --no-fail-on-empty-changeset

# Step 4: Print outputs
echo "[4/4] Done."
echo ""

APP_URL=$(aws cloudformation describe-stacks \
  --stack-name "$STACK_NAME" \
  --region "$REGION" \
  --query "Stacks[0].Outputs[?OutputKey=='AppUrl'].OutputValue" \
  --output text)

echo "=================================="
echo "  Travel Planner: $APP_URL"
echo "=================================="
echo ""
echo "Open the URL in your browser to plan a trip."
