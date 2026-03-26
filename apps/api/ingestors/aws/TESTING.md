# AWS Discovery & Export Testing Guide

This guide covers how to test the AWS infrastructure discovery pipeline and the export to MinIO.

## 1. Local Environment Setup

Ensure your `.env` contains the dedicated MinIO credentials to avoid clashing with real AWS:

```ini
# apps/api/.env
OPSCRIBE_MINIO_USER=minioadmin
OPSCRIBE_MINIO_PASSWORD=minioadmin
AWS_S3_ENDPOINT_URL=http://localhost:9000
OPSCRIBE_S3_BUCKET=opscribe-data
```

Start the services:
```bash
docker compose up -d
npm run dev
```

---

## 2. CLI Testing (Individual Services)

Use the standalone test script to verify connectivity and Role Assumption.

```bash
# From repo root
source apps/api/venv/bin/activate
PYTHONPATH=. python3 -m tests.unit.discovery.test_aws_detector \
  --role-arn arn:aws:iam::ACCOUNT_ID:role/ROLE_NAME \
  --services ec2 s3
```

---

## 3. End-to-End Pipeline Testing (UI/API)

The pipeline triggers a background task that discovers AWS/GitHub and saves a JSON dump to MinIO.

### Trigger via cURL
Use the default developer client ID seen in local logs:

```bash
curl -X POST http://localhost:8000/pipeline/export \
     -H "Content-Type: application/json" \
     -d '{
       "client_id": "00000000-0000-0000-0000-000000000000",
       "include_aws": true,
       "include_github": false,
       "aws_region": "us-east-1"
     }'
```

### Verify in MinIO
1. Open **[http://localhost:9001](http://localhost:9001)** (admin/admin).
2. Go to the `opscribe-data` bucket.
3. You should see a folder named `00000000-0000-0000-0000-000000000000`.
4. Inside, `latest.json` contains the serialized discovery results.

---

## 4. IAM Requirements (Reminder)

### Opscribe Identity (The Parser)
Must be an **IAM User** (not root) with `sts:AssumeRole` permissions.
Configure this via `aws configure` on your machine.

### Client Account (The Target)
Must have an **IAM Role** with:
1. **Trust Policy** allowing the Parser User ARN.
2. **Permissions Policy** (e.g., `ReadOnlyAccess`).
