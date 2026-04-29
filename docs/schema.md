# Data Schemas

This document defines the shared data contracts for the repository. These schemas must be respected by all feature branches to ensure interoperability.

## Week 1: TopicItem Schema (Canonical)

This is the primary schema for the ingestion and normalization phase.

```json
{
  "id": "string",                  // Unique ID (e.g., SHA256 hash of URL)
  "title": "string",               // Cleaned title of the topic
  "url": "string",                 // Original source URL
  "source": "string",              // Name of the source (e.g., "arxiv", "openai_blog")
  "published_at": "ISO-8601",      // Date/time of publication
  "author": "string | null",       // Author name if available
  "raw_text": "string",            // Full extracted text or significant excerpt
  "excerpt": "string | null",      // Brief summary/teaser from the source
  "category": "string",            // paper | repo | release | concept | news | tool
  "topic_tags": ["string"],        // List of relevant keywords
  "status": "string",              // raw | staged | scored | approved | rejected
  "metadata": {                    // Any additional source-specific fields
    "source_type": "rss | html | manual"
  }
}
```

### Allowed Week 1 Status Values
- `raw`: Initial extraction, unvalidated.
- `staged`: Schema-validated and saved to local storage.
- `rejected`: Explicitly dropped due to quality or duplication issues.

## Raw vs Staged Data
- **Raw Data (`data/raw/`):** The exact response or file fetched from the source (e.g., XML, HTML, JSON). Preserved for auditing.
- **Staged Data (`data/staged/`):** JSON files following the `TopicItem` schema. These are the inputs for the Scoring module.

## Traceability & Unknown Values
- If a required field is missing from the source, it **must** be set to `"unknown"`.
- Do **not** attempt to guess missing dates or authors.
- The `id` must be deterministic based on the `url` to prevent duplicates.

## Schema Change Policy
- Shared schemas are **frozen** during parallel development.
- Proposals for schema changes must be documented here and merged into `main` before being adopted by feature branches.
- Use optional fields (nullable) for experimental additions before formalizing them.

## Future Schemas (Drafts)
The following schemas will be formalized in Weeks 2 and 3:
- **Brief Schema:** Summarization and educational framing.
- **Script Schema:** Multi-format content drafts.
- **Asset Schema:** Thumbnail prompts and metadata.
