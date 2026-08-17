# Part 2: ARD Registry - Installation

Deploys a searchable ARD registry on AWS that indexes partner agent catalogs and serves `POST /search` queries with ranked results.

## What gets deployed

- S3 bucket (stores partner catalogs and Lambda code)
- CloudFront distribution (serves catalogs publicly)
- Lambda function (search logic with keyword scoring)
- API Gateway HTTP API (`POST /search` endpoint)
- IAM role (Lambda reads from S3)

## Prerequisites

- AWS CLI configured with credentials
- `zip` utility available
- AWS account with CloudFormation permissions

## Directory structure

```
part2-install/
├── catalogs/
│   ├── partnerA.json    # Flight & Hotel Specialist catalog
│   └── partnerB.json    # Payment Processing + Currency Exchange catalog
├── lambda/
│   └── handler.py       # Search Lambda (keyword overlap scoring)
├── deploy.sh            # Deployment script
├── search-ui.html       # Browser-based search UI for testing
└── template.yaml        # CloudFormation template
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

The script creates the S3 bucket, uploads catalogs and Lambda code, then deploys the CloudFormation stack. It prints the registry URL when done.

## Test

**Using the search UI:**

```bash
python3 -m http.server 8080
```

Open `http://localhost:8080/search-ui.html` in your browser.

**Using curl:**

```bash
curl -s -X POST "https://<api-id>.execute-api.us-west-2.amazonaws.com/search" \
  -H "Content-Type: application/json" \
  -d '{"query":{"text":"flight hotel booking"},"pageSize":5}' | python3 -m json.tool
```

## Teardown

```bash
aws s3 rm s3://<bucket-name> --recursive
aws cloudformation delete-stack --stack-name ard-registry --region us-west-2
```
