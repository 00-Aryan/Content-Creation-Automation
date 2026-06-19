# LinkedIn Quality Scoring

This document explains the deterministic LinkedIn quality scoring rules used by the LinkedIn generation path.

The quality score is attached to generated LinkedIn posts through the `quality_score` field on `LinkedInPost`. The generator uses this result as a safety layer. If any deterministic quality gate fails, the generated post is forced to `NEEDS_REVIEW`.

Related documents:

- `docs/platform/linkedin-content-contract.md`
- `docs/platform/platform-quality-gates.md`
- `docs/tasks/task_089.md`
- `docs/tasks/task_090.md`
- `docs/tasks/task_091.md`

---

## Purpose

The LinkedIn quality evaluator gives operators and future agents a deterministic explanation for why a generated LinkedIn post is safe to keep as a draft or must be routed to review.

The evaluator does not call an LLM. It does not make network requests. It only inspects the generated LinkedIn post object.

---

## Evaluated fields

The evaluator currently checks these fields:

- `hook`
- `post_body`
- `takeaway`
- `cta`
- `hashtags`
- `source_reference`
- `source_links`

The final quality result contains:

- `overall_score`
- `passed`
- `gate_results`
- `issues`
- `warnings`

---

## Implemented gates

| Gate | Pass condition | Failure message |
|---|---|---|
| `hashtags` | `hashtags` must be a list with 3 to 5 items. | `Hashtag count must be between 3 and 5.` |
| `cta` | `cta` must be non-empty and contain exactly one `?` character. | `CTA must contain exactly one question prompt.` |
| `length` | Combined `hook`, `post_body`, `takeaway`, and `cta` length must be between 1 and 3000 characters. | `Post length must be between 1 and 3000 characters.` |
| `hook` | `hook` must be present, must not be `needs_review`, must be at most 180 characters, and must use no more than 2 non-empty lines. | `Hook must be present, not needs_review, concise, and no more than 2 lines.` |
| `source` | `source_reference` must be present and not `needs_review`; `source_links` must be a list with at least one non-empty link. | `Source reference and at least one source link are required.` |
| `banned_hype_language` | `hook`, `post_body`, `takeaway`, and `cta` must not contain banned hype phrases. | `Post contains banned hype language: <matched phrases>` |

---

## Banned hype phrases

The current banned phrase list is deterministic:

- `game-changing`
- `mind-blowing`
- `insane`
- `guaranteed`
- `secret hack`
- `ultimate guide`
- `you won't believe`

The evaluator checks these phrases against lowercased text from:

- `hook`
- `post_body`
- `takeaway`
- `cta`

It does not currently check hashtags, source references, source links, or claims for banned hype language.

---

## Score interpretation

Each gate receives one of two scores:

| Gate result | Gate score |
|---|---:|
| Passed | 100 |
| Failed | 0 |

The overall score is the rounded average of all gate scores.

Since there are six gates, common scores are:

| Failed gates | Overall score | `passed` |
|---:|---:|---|
| 0 | 100 | `true` |
| 1 | 83 | `false` |
| 2 | 67 | `false` |
| 3 | 50 | `false` |
| 4 | 33 | `false` |
| 5 | 17 | `false` |
| 6 | 0 | `false` |

A post only passes when every gate passes.

---

## Review-status behavior

The LinkedIn generator attaches the quality result before returning the post.

If `quality_score.passed` is `false`, the generator forces:

    review_status = NEEDS_REVIEW

If `quality_score.passed` is `true`, the generator preserves the post's existing review status. For normal valid generated posts, this allows the post to remain:

    review_status = DRAFT

Fallback posts are also evaluated and remain `NEEDS_REVIEW`.

---

## Passing example

Input post:

    {
      "topic_id": "topic_123",
      "hook": "What if attention is the missing mental model?",
      "post_body": "Transformers are easier to understand when attention is treated as a relevance filter over tokens.",
      "takeaway": "Start with attention before jumping into full architectures.",
      "cta": "What part of Transformers confused you first?",
      "hashtags": ["#AI", "#MachineLearning", "#Transformers"],
      "source_reference": "Paper: Attention Is All You Need",
      "source_links": ["https://arxiv.org/abs/1706.03762"],
      "claims_used": ["Transformers use attention to process token relationships."],
      "review_status": "draft"
    }

Expected quality result summary:

    {
      "overall_score": 100,
      "passed": true,
      "issues": [],
      "warnings": []
    }

Expected review status:

    DRAFT

---

## Failing example

Input post:

    {
      "topic_id": "topic_123",
      "hook": "needs_review",
      "post_body": "This is a game-changing secret hack for learning Transformers.",
      "takeaway": "Start here.",
      "cta": "Share your thoughts. What confused you first? What helped?",
      "hashtags": ["#AI", "#ML"],
      "source_reference": "",
      "source_links": [],
      "claims_used": ["Transformers use attention to process text."],
      "review_status": "draft"
    }

Expected failed gates:

| Gate | Reason |
|---|---|
| `hashtags` | Only 2 hashtags were provided. |
| `cta` | CTA contains 2 question marks instead of exactly 1. |
| `hook` | Hook is `needs_review`. |
| `source` | Source reference is blank and source links are empty. |
| `banned_hype_language` | Text contains `game-changing` and `secret hack`. |

Expected issue messages:

    [
      "Hashtag count must be between 3 and 5.",
      "CTA must contain exactly one question prompt.",
      "Hook must be present, not needs_review, concise, and no more than 2 lines.",
      "Source reference and at least one source link are required.",
      "Post contains banned hype language: game-changing, secret hack"
    ]

Expected quality result summary:

    {
      "overall_score": 17,
      "passed": false,
      "warnings": []
    }

Expected review status:

    NEEDS_REVIEW

---

## Operator notes

Use the quality score as a routing signal, not as a complete creative-quality judgment.

A post can pass all deterministic gates and still need human editing for voice, originality, or strategic positioning. The current evaluator only checks implemented platform-safety and structure rules.

Do not assume the evaluator checks:

- factual correctness
- claim-source alignment
- tone quality beyond banned hype phrases
- audience fit
- originality
- plagiarism
- LinkedIn engagement prediction
- image or carousel quality

Those are separate future validation concerns.
