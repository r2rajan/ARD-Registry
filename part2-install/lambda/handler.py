"""ARD Registry Lambda - POST /search (ARD spec section 7.2).

Loads partner catalogs from S3 at cold start, merges entries from all
partners into a single index, scores against incoming queries using
keyword overlap, applies filters, and returns ranked results with
source attribution.
"""

import base64
import json
import os
import re

import boto3

# Load catalogs from S3 at cold start
S3_BUCKET = os.environ["CATALOG_BUCKET"]
CATALOGS_PREFIX = os.environ.get("CATALOGS_PREFIX", "catalogs/")

s3 = boto3.client("s3")

# Merge all partner catalogs into a flat list of entries, each tagged with source
ENTRIES = []


def _load_catalogs():
    """Load all catalog JSON files from the S3 prefix."""
    paginator = s3.get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=S3_BUCKET, Prefix=CATALOGS_PREFIX):
        for obj in page.get("Contents", []):
            key = obj["Key"]
            if not key.endswith(".json"):
                continue
            resp = s3.get_object(Bucket=S3_BUCKET, Key=key)
            catalog = json.loads(resp["Body"].read())
            source = catalog.get("host", {}).get("identifier", key)
            for entry in catalog.get("entries", []):
                entry["_source"] = source
                ENTRIES.append(entry)


_load_catalogs()


def tokenize(text):
    """Split text into lowercase word tokens."""
    return set(re.findall(r"[a-z0-9]+", text.lower()))


def score_entry(entry, query_tokens):
    """Score an entry 0-100 based on keyword overlap with the query.

    Weights:
      displayName            30 pts
      description            25 pts
      representativeQueries  25 pts
      capabilities           10 pts
      tags                   10 pts
    """
    if not query_tokens:
        return 50

    score = 0
    fields = [
        ("displayName", 30),
        ("description", 25),
        ("representativeQueries", 25),
        ("capabilities", 10),
        ("tags", 10),
    ]

    for field, weight in fields:
        value = entry.get(field, "")
        if isinstance(value, list):
            value = " ".join(value)
        field_tokens = tokenize(value)
        overlap = len(field_tokens & query_tokens)
        score += int(overlap / max(len(query_tokens), 1) * weight)

    return min(score, 100)


def apply_filters(entries, filters):
    """Apply type and tags filters per ARD section 7.1."""
    result = entries

    type_filter = filters.get("type")
    if type_filter:
        if isinstance(type_filter, str):
            type_filter = [type_filter]
        result = [e for e in result if e.get("type") in type_filter]

    tags_filter = filters.get("tags")
    if tags_filter:
        if isinstance(tags_filter, str):
            tags_filter = [tags_filter]
        result = [
            e for e in result
            if any(t in e.get("tags", []) for t in tags_filter)
        ]

    return result


def search(body):
    """Execute an ARD search across indexed catalog entries."""
    query = body.get("query", {})
    query_text = query.get("text", "")
    filters = query.get("filter", {})
    page_size = body.get("pageSize", 5)

    filtered = apply_filters(ENTRIES, filters)

    query_tokens = tokenize(query_text)
    scored = []
    for entry in filtered:
        scored.append({
            "identifier": entry.get("identifier"),
            "displayName": entry.get("displayName"),
            "type": entry.get("type"),
            "url": entry.get("url"),
            "score": score_entry(entry, query_tokens),
            "source": entry.get("_source"),
        })

    scored.sort(key=lambda x: x["score"], reverse=True)

    # Remove None values
    results = [
        {k: v for k, v in r.items() if v is not None}
        for r in scored[:page_size]
    ]

    return {"results": results}


def lambda_handler(event, context):
    """AWS Lambda entry point for API Gateway v2 (HTTP API)."""
    body_str = event.get("body")
    is_base64 = event.get("isBase64Encoded", False)

    if body_str and is_base64:
        body_str = base64.b64decode(body_str).decode("utf-8")

    if not body_str:
        body_str = "{}"

    try:
        body = json.loads(body_str)
    except (json.JSONDecodeError, TypeError):
        return {
            "statusCode": 400,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"error": "Invalid JSON body"}),
        }

    result = search(body)

    return {
        "statusCode": 200,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Content-Type",
            "Access-Control-Allow-Methods": "POST,OPTIONS",
        },
        "body": json.dumps(result),
    }
