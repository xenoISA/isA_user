# Storage

File storage, media processing, and content management.

## Overview

Content management is handled by four services:

| Service | Port | Purpose |
|---------|------|---------|
| storage_service | 8209 | File upload, sharing, versioning |
| album_service | 8219 | Photo albums, collections |
| media_service | 8222 | Transcoding, thumbnails |
| document_service | 8227 | Documents, OCR, text extraction |

## Storage Service (8209)

### Upload File

```bash
curl -X POST "http://localhost:8209/api/v1/storage/upload" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -F "file=@/path/to/photo.jpg" \
  -F "folder=photos" \
  -F "metadata={\"description\": \"Vacation photo\"}"
```

Response:
```json
{
  "file_id": "file_abc123",
  "filename": "photo.jpg",
  "size": 2048576,
  "mime_type": "image/jpeg",
  "url": "https://storage.example.com/file_abc123",
  "thumbnail_url": "https://storage.example.com/file_abc123/thumb",
  "created_at": "2024-01-28T10:30:00Z"
}
```

### Download File

```bash
curl "http://localhost:8209/api/v1/storage/files/file_abc123/download" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -o downloaded_file.jpg
```

### List Files

```bash
curl "http://localhost:8209/api/v1/storage/files?folder=photos&limit=20" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

### Delete File

```bash
curl -X DELETE "http://localhost:8209/api/v1/storage/files/file_abc123" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

### File Sharing

#### Create Public Link

```bash
curl -X POST "http://localhost:8209/api/v1/storage/files/file_abc123/share" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "visibility": "public",
    "expires_in_days": 7
  }'
```

#### Password-Protected Share

```bash
curl -X POST "http://localhost:8209/api/v1/storage/files/file_abc123/share" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "visibility": "password",
    "password": "secret123",
    "expires_in_days": 30
  }'
```

#### Share with Users

```bash
curl -X POST "http://localhost:8209/api/v1/storage/files/file_abc123/share" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "visibility": "private",
    "shared_with": ["user_456", "user_789"],
    "permission": "view"
  }'
```

### Storage Quota

```bash
curl "http://localhost:8209/api/v1/storage/quota" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

Response:
```json
{
  "used": 5368709120,
  "limit": 10737418240,
  "used_formatted": "5 GB",
  "limit_formatted": "10 GB",
  "percentage": 50
}
```

### Photo Versioning

```bash
# Get photo versions
curl "http://localhost:8209/api/v1/storage/files/file_abc123/versions" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"

# Restore version
curl -X POST "http://localhost:8209/api/v1/storage/files/file_abc123/versions/v2/restore" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

## Album Service (8219)

### Create Album

```bash
curl -X POST "http://localhost:8219/api/v1/albums" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Summer Vacation 2024",
    "description": "Photos from our trip",
    "cover_file_id": "file_abc123"
  }'
```

### Add Photos to Album

```bash
curl -X POST "http://localhost:8219/api/v1/albums/album_123/photos" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "file_ids": ["file_abc123", "file_def456", "file_ghi789"]
  }'
```

### Get Album

```bash
curl "http://localhost:8219/api/v1/albums/album_123" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

### Share Album

```bash
curl -X POST "http://localhost:8219/api/v1/albums/album_123/share" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "shared_with": ["user_456"],
    "can_add_photos": true
  }'
```

### Collaborative Albums

```bash
# Family album (via organization)
curl -X POST "http://localhost:8219/api/v1/albums" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Family Photos",
    "organization_id": "org_family_123",
    "collaborative": true
  }'
```

## Media Service (8222)

### Generate Thumbnail

```bash
curl -X POST "http://localhost:8222/api/v1/media/thumbnail" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "file_id": "file_abc123",
    "width": 200,
    "height": 200,
    "format": "webp"
  }'
```

### Transcode Video

```bash
curl -X POST "http://localhost:8222/api/v1/media/transcode" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "file_id": "file_video123",
    "output_format": "mp4",
    "quality": "720p",
    "codec": "h264"
  }'
```

### Get Transcoding Status

```bash
curl "http://localhost:8222/api/v1/media/jobs/job_123" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

### Supported Formats

| Input | Output | Operations |
|-------|--------|------------|
| JPEG, PNG, WebP | JPEG, PNG, WebP, AVIF | Resize, crop, rotate |
| MP4, MOV, AVI | MP4, WebM | Transcode, compress |
| MP3, WAV, M4A | MP3, AAC | Convert, normalize |

## Document Service (8227)

### Upload Document

```bash
curl -X POST "http://localhost:8227/api/v1/documents" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -F "file=@/path/to/document.pdf" \
  -F "extract_text=true"
```

### Get Document with OCR

```bash
curl "http://localhost:8227/api/v1/documents/doc_123?include_text=true" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

Response:
```json
{
  "document_id": "doc_123",
  "filename": "contract.pdf",
  "pages": 5,
  "extracted_text": "This agreement is made between...",
  "metadata": {
    "author": "John Doe",
    "created": "2024-01-15"
  }
}
```

### Document Versions

```bash
# Upload new version
curl -X POST "http://localhost:8227/api/v1/documents/doc_123/versions" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -F "file=@/path/to/document_v2.pdf"

# Get version history
curl "http://localhost:8227/api/v1/documents/doc_123/versions" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

## Intelligent Features

### Semantic Search

```bash
curl -X POST "http://localhost:8209/api/v1/storage/search" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "sunset beach vacation",
    "type": "semantic",
    "limit": 20
  }'
```

### AI Indexing

Files are automatically indexed with AI-extracted metadata:

```json
{
  "file_id": "file_abc123",
  "ai_metadata": {
    "labels": ["beach", "sunset", "ocean"],
    "description": "A sunset over the ocean with waves",
    "dominant_colors": ["orange", "blue", "purple"],
    "faces_detected": 0
  }
}
```

### RAG Integration

```bash
# Search files for RAG context
curl -X POST "http://localhost:8209/api/v1/storage/rag/search" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What documents mention the project deadline?",
    "file_types": ["pdf", "docx"],
    "top_k": 5
  }'
```

## Python SDK

```python
from isa_user import StorageClient, AlbumClient

storage = StorageClient("http://localhost:8209")
albums = AlbumClient("http://localhost:8219")

# Upload file
file = await storage.upload(
    token=access_token,
    file_path="/path/to/photo.jpg",
    folder="photos"
)

# Create album
album = await albums.create(
    token=access_token,
    name="Vacation 2024",
    file_ids=[file.file_id]
)

# Share album
await albums.share(
    token=access_token,
    album_id=album.album_id,
    user_ids=["user_456"]
)

# Semantic search
results = await storage.search(
    token=access_token,
    query="beach sunset",
    type="semantic"
)
```

## Next Steps

- [Organizations](./organizations) - Multi-tenant & family sharing
- [Memory](./memory) - AI cognitive memory
- [Payments](./payments) - Payment processing
