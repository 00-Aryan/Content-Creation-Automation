# Chapter 2 — Ingestion: From RSS to TopicItem

## The Question

Why is ingestion its own stage? Why not just fetch a feed and immediately score it?

Because raw data is messy, inconsistent, and source-specific. An arXiv entry has different fields than an OpenAI blog post. If scoring logic had to handle raw XML quirks, every new source would require changes to the scoring engine. Ingestion exists to normalize chaos into a single, validated schema — `TopicItem` — so that everything downstream never thinks about where data came from.

## The Answer

The ingestion stage fetches raw feeds, parses entries, normalizes each into a `TopicItem`, deduplicates by URL-derived ID, and persists both the raw payload (for auditing) and the validated item (for processing). What enters is XML/Atom. What leaves is a JSON file per topic in `data/staged/` conforming exactly to the TopicItem schema.

## Files in This Stage

### collectors/base.py
**Why it exists:** Defines the contract that all collectors must follow.
**What it does:** `BaseCollector` is an abstract class with three methods: `fetch()` (get raw data), `parse()` (extract records), `normalize()` (convert one record to TopicItem). The `collect()` method orchestrates all three with error handling — if fetch fails, return empty list; if one record fails normalization, skip it and continue.
**Key decision:** The three-method split (fetch/parse/normalize) means you can test normalization logic without making network calls, and you can swap the fetch mechanism without touching parsing.
**Connects to:** Receives source_config from feeds.yaml → sends List[TopicItem] to storage.

### collectors/rss.py
**Why it exists:** Implements the base contract for RSS/Atom feeds specifically.
**What it does:** `RSSCollector` uses feedparser to fetch and parse feeds. It handles the "bozo" flag (malformed feeds that still have usable entries), extracts publication dates from multiple possible fields (`published_parsed`, `updated_parsed`, `created_parsed`), handles missing authors defensively, and maps feed categories from config.
**Key decision:** The bozo flag is logged as a warning but doesn't abort — many real-world feeds are technically malformed but contain valid entries. Only if there are zero entries does it raise.
**Connects to:** Receives feed URL from config → sends TopicItems to LocalStorage.save_staged().

## Data Flow

```
config/feeds.yaml (url, source, category)
    ↓
RSSCollector.fetch()
    ↓
feedparser.parse(url) → FeedParserDict (raw XML parsed)
    ↓
RSSCollector.parse() → List[Dict] (one dict per entry)
    ↓
RSSCollector.normalize() per entry
    ↓
TopicItem(
    id=SHA256(url),
    title, url, source, published_at,
    author, raw_text, excerpt,
    category, topic_tags, status="raw"
)
    ↓
LocalStorage.save_raw()   → data/raw/{source}_{timestamp}.json
LocalStorage.save_staged() → data/staged/{id}.json
```

## Why Not the Alternative?

**Why not scrape websites directly?** Scraping is brittle — HTML structure changes without notice, requires per-site selectors, and raises legal concerns. RSS/Atom feeds are a published API: structured, stable, and explicitly intended for machine consumption. When a feed breaks, feedparser's bozo flag tells you immediately. When a website changes its CSS, your scraper silently returns garbage.

## Key Insight

**Ingestion's job is to make the rest of the pipeline source-agnostic — after this stage, no downstream code ever needs to know whether a topic came from arXiv or a blog.**
