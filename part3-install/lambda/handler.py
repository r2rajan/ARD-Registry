"""ARD Registry Lambda (improved) - POST /search with dual scoring.

Loads partner catalogs from S3 at cold start. Returns results scored
with both keyword overlap (stop words + stemming) AND vector embeddings
(Titan Embeddings v2 via Bedrock). The API returns both scores so
callers can compare approaches.

Improvements over Part 2:
- Fix 1: Stop words removed before scoring
- Fix 2: Basic suffix stemming (flights → flight)
- Fix 4: Vector embeddings via Amazon Bedrock Titan Embeddings v2
"""

import base64
import json
import math
import os
import re

import boto3

# Load catalogs from S3 at cold start
S3_BUCKET = os.environ["CATALOG_BUCKET"]
CATALOGS_PREFIX = os.environ.get("CATALOGS_PREFIX", "catalogs/")

s3 = boto3.client("s3")
bedrock = boto3.client("bedrock-runtime")

# Merge all partner catalogs into a flat list of entries, each tagged with source
ENTRIES = []
ENTRY_EMBEDDINGS = []  # parallel list of embedding vectors

# --- Fix 1: Stop word removal ---
STOP_WORDS = {
    "a", "an", "the", "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "do", "does", "did", "will", "would", "could",
    "should", "may", "might", "shall", "can", "need", "to", "of", "in",
    "for", "on", "with", "at", "by", "from", "as", "into", "through",
    "during", "before", "after", "above", "below", "between", "out", "off",
    "over", "under", "again", "further", "then", "once", "i", "me", "my",
    "we", "you", "it", "he", "she", "they", "this", "that", "these",
    "those", "am", "its", "your", "our", "their", "what", "which", "who",
    "whom", "when", "where", "why", "how", "all", "each", "every", "both",
    "few", "more", "most", "other", "some", "such", "no", "nor", "not",
    "only", "own", "same", "so", "than", "too", "very", "just", "and",
    "but", "or", "if", "while", "about", "up", "down", "here", "there",
}


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


def _entry_text(entry):
    """Combine all searchable fields of an entry into one text blob for embedding."""
    parts = []
    for field in ["displayName", "description", "representativeQueries", "capabilities", "tags"]:
        value = entry.get(field, "")
        if isinstance(value, list):
            value = " ".join(value)
        if value:
            parts.append(value)
    return " ".join(parts)


def _embed(text):
    """Get embedding vector from Bedrock Titan Embeddings v2."""
    response = bedrock.invoke_model(
        modelId="amazon.titan-embed-text-v2:0",
        # Titan v2 max is 8192 tokens
        body=json.dumps({"inputText": text[:8000]})
    )
    result = json.loads(response["body"].read())
    return result["embedding"]


def _cosine_similarity(vec_a, vec_b):
    """Compute cosine similarity between two vectors."""
    dot = sum(a * b for a, b in zip(vec_a, vec_b))
    mag_a = math.sqrt(sum(a * a for a in vec_a))
    mag_b = math.sqrt(sum(b * b for b in vec_b))
    if mag_a == 0 or mag_b == 0:
        return 0.0
    return dot / (mag_a * mag_b)


def _build_embeddings():
    """Pre-compute embeddings for all catalog entries at cold start."""
    for entry in ENTRIES:
        text = _entry_text(entry)
        embedding = _embed(text)
        ENTRY_EMBEDDINGS.append(embedding)


_load_catalogs()
_build_embeddings()


# --- Fix 2: Basic stemming ---
def stem(word):
    """Simple suffix-stripping stemmer for common English patterns."""
    if len(word) <= 3:
        return word

    if word.endswith("tion"):
        return word[:-4] + "te" if len(word) > 6 else word[:-4]
    if word.endswith("sion"):
        return word[:-4]
    if word.endswith("ness"):
        return word[:-4]
    if word.endswith("ment"):
        return word[:-4]
    if word.endswith("ing"):
        base = word[:-3]
        if len(base) >= 3:
            return base
    if word.endswith("ies"):
        return word[:-3] + "y"
    if word.endswith("es"):
        base = word[:-2]
        if len(base) >= 3:
            return base
    if word.endswith("ed"):
        base = word[:-2]
        if len(base) >= 3:
            return base
    if word.endswith("ly"):
        base = word[:-2]
        if len(base) >= 3:
            return base
    if word.endswith("s") and not word.endswith("ss"):
        base = word[:-1]
        if len(base) >= 3:
            return base

    return word


def tokenize(text):
    """Split text into lowercase word tokens, remove stop words, apply stemming."""
    raw_tokens = set(re.findall(r"[a-z0-9]+", text.lower()))
    meaningful = raw_tokens - STOP_WORDS
    return {stem(t) for t in meaningful}


def score_keyword(entry, query_tokens):
    """Score an entry 0-100 based on keyword overlap (Fix 1 + Fix 2)."""
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


def score_vector(entry_index, query_embedding):
    """Score an entry 0-100 based on cosine similarity with the query embedding."""
    if entry_index >= len(ENTRY_EMBEDDINGS):
        return 0
    similarity = _cosine_similarity(
        ENTRY_EMBEDDINGS[entry_index], query_embedding)
    # Convert cosine similarity (0.0-1.0) to 0-100 scale
    return int(max(0, similarity) * 100)


def apply_filters(entries_with_index, filters):
    """Apply type and tags filters per ARD section 7.1."""
    result = entries_with_index

    type_filter = filters.get("type")
    if type_filter:
        if isinstance(type_filter, str):
            type_filter = [type_filter]
        result = [(i, e) for i, e in result if e.get("type") in type_filter]

    tags_filter = filters.get("tags")
    if tags_filter:
        if isinstance(tags_filter, str):
            tags_filter = [tags_filter]
        result = [
            (i, e) for i, e in result
            if any(t in e.get("tags", []) for t in tags_filter)
        ]

    return result


def search(body):
    """Execute an ARD search returning both keyword and vector scores."""
    query = body.get("query", {})
    query_text = query.get("text", "")
    filters = query.get("filter", {})
    page_size = body.get("pageSize", 5)

    # Prepare indexed entries for filtering
    indexed_entries = list(enumerate(ENTRIES))
    filtered = apply_filters(indexed_entries, filters)

    # Keyword scoring
    query_tokens = tokenize(query_text)

    # Vector scoring - embed the query
    query_embedding = _embed(query_text) if query_text else None

    scored = []
    for idx, entry in filtered:
        kw_score = score_keyword(entry, query_tokens)
        vec_score = score_vector(
            idx, query_embedding) if query_embedding else 0

        scored.append({
            "identifier": entry.get("identifier"),
            "displayName": entry.get("displayName"),
            "type": entry.get("type"),
            "url": entry.get("url"),
            "keywordScore": kw_score,
            "vectorScore": vec_score,
            "score": vec_score,  # primary ranking by vector score
            "source": entry.get("_source"),
        })

    # Sort by vector score (primary)
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
