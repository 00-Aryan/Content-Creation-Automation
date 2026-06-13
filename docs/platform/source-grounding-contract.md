# Source Grounding Contract

This document defines the requirements and schemas for ensuring that all generated content is rigorously grounded in primary source material, preventing hallucinations and preserving technical traceability.

---

## 1. Core Principles

All platform-specific generators must comply with the following grounding rules:

1. **Direct Ingestion Traceability**: Every fact, metric, formula, or quote in the generated output must be mapped back to an ingested source document (e.g., a specific section, page, or table in an arXiv PDF).
2. **Strict Exclusion of External Knowledge**: Generators must not inject facts or figures that are not present in the input brief. If a fact is not in the source brief, it cannot appear in the output.
3. **Trace Logs**: The generation pipeline must output a structured trace log mapping each sentence of the output to its source section in the input brief.

---

## 2. Grounding Metadata Schema

Every generated asset must include a `grounding_map` key in its payload containing the following structure:

```json
{
  "grounding_map": [
    {
      "output_sentence": "FlashAttention-3 achieves up to 75% utilization of the theoretical H100 GPU limits.",
      "source_reference": {
        "source_id": "arxiv:2407.00215",
        "citation_key": "dao2024flashattention3",
        "location": "Section 5.1, Table 1 (Page 8)",
        "exact_quote_or_fact": "FlashAttention-3 achieves 75% of GEMM throughput on H100 SXM5 GPUs."
      }
    }
  ]
}
```

---

## 3. Reference Requirements

| Element | Grounding Rule | Example |
| :--- | :--- | :--- |
| **Metrics / Figures** | Must match the exact numbers reported in the paper. No rounding that changes significance. | "75% utilization" (Correct) vs. "Almost 80% utilization" (Incorrect). |
| **Quotes** | Direct quotes must be enclosed in quotation marks and match the source text character-for-character. | "exploiting asymmetric memory hierarchies..." |
| **Equations** | Mathematical representations must retain the correct variable mappings. | "O(N^2) complexity" must not be simplified to "linear time". |

---

## 4. Verification and Auditing

The system maintains a verification engine that checks for compliance:
* **Lexical Matcher**: Automatically verifies that numeric values and capitalized technical terms in the generated post exist in the source brief.
* **Citation Validator**: Confirms that all `source_id` entries match keys defined in the project's SQLite database.
* **Audit Trail**: Saves the `grounding_map` alongside the generated post in the database under `audit.db` to allow human reviewers to audit the claims before approval.
