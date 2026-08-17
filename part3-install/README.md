# Part 3: Improved Scoring - Installation

Upgrades the Part 2 registry Lambda with stop word removal, stemming, and vector embeddings via Amazon Bedrock Titan Embeddings v2. Returns both `keywordScore` and `vectorScore` for comparison.

## What gets changed

- Lambda function code updated (dual scoring: keyword + vector)
- Bedrock `InvokeModel` permission added to the Lambda role
- Lambda timeout increased to 60s, memory to 512MB (embedding calls at cold start)

The rest of the infrastructure (S3, CloudFront, API Gateway, catalogs) stays unchanged from Part 2.

## Prerequisites

- Part 2 stack already deployed (`ard-registry` CloudFormation stack)
- AWS CLI configured with credentials
- Amazon Bedrock Titan Embed Text v2 model access enabled in your region

### Enable Titan Embeddings in Bedrock

If not already enabled:

1. Go to the [Bedrock console](https://console.aws.amazon.com/bedrock/)
2. Navigate to Model access
3. Request access to "Titan Embeddings G1 - Text v2"
4. Wait for access to be granted (usually instant)

## Directory structure

```
part3-install/
├── lambda/
│   └── handler.py       # Improved Lambda (stop words + stemming + embeddings)
├── deploy.sh            # Updates existing Part 2 stack
├── search-ui.html       # Comparison UI (keyword vs vector side by side)
└── README.md
```

## Deploy

```bash
chmod +x deploy.sh
./deploy.sh
```

Or with a custom bucket name and region:

```bash
./deploy.sh my-bucket-name us-west-2
```

The script uploads the new Lambda code, adds Bedrock permissions, and updates the function configuration.

## Test

**Using the comparison UI:**

```bash
python3 -m http.server 8080
```

Open `http://localhost:8080/search-ui.html` in your browser. Results show keyword and vector scores side by side.

**Using curl:**

```bash
curl -s -X POST "https://<api-id>.execute-api.us-west-2.amazonaws.com/search" \
  -H "Content-Type: application/json" \
  -d '{"query":{"text":"I need to pay for my trip"},"pageSize":3}' | python3 -m json.tool
```

Response now includes both scores:

```json
{
  "results": [
    {
      "displayName": "Payment Processing Agent (A2A)",
      "keywordScore": 32,
      "vectorScore": 23,
      "score": 23,
      "source": "did:web:partnerB.com"
    }
  ]
}
```

## Queries that show the semantic advantage

| Query | Keyword score | Vector score | Winner |
|-------|---|---|---|
| "flight hotel booking" | 77 | ~42 | Keyword (exact tokens match) |
| "I need to pay for my trip" | ~0 | 23 | Vector (semantic understanding) |
| "help me convert dollars to yen" | 12 | 34 | Vector (no exact word overlap) |

## Rollback to Part 2 scoring

To revert to keyword-only scoring, redeploy from Part 2:

```bash
cd ../part2-install
./deploy.sh
```
