# personas/sample_data/forms — License Notes

## test_template.hwpx

Derivative of `Skeleton.hwpx` from
`@ubermensch1218/hwpxcore@0.1.3` (MIT License,
https://www.npmjs.com/package/@ubermensch1218/hwpxcore).

Modifications: a single 3-row × 2-col table (id=`999000001`) was injected into
`Contents/section0.xml` so that `HwpxEditor.set_cell` /
`HwpxEditor.replace_in_cell` have a target during T17 unit tests. No
proprietary or confidential content. Redistributable under the MIT terms of
the upstream package — see upstream LICENSE for full text.

This fixture is **for tests only**. It is not a real Korean government grant
form template.

## grant_application_template.hwpx (T18 stand-in)

This file is a **MIT-licensed stand-in**, not a real Korean government grant
form. It is the same Skeleton.hwpx derivative as `test_template.hwpx`, but
with an 8-row × 2-col table (id=`999000002`) injected via
`personas/scripts/build_grant_template.py`. The eight left-column labels
mimic typical grant fields (회사명·대표자명·사업자등록번호·사업분야·
신청금액·매출액·직원수·신청일자) so case06 can exercise the full
`fill_form` → `extract_text` round-trip end-to-end.

### Why a stand-in instead of a real govt form

Real templates from TIPA, SMTECH, K-Startup, and similar agencies typically
carry an implicit "applicant use" license, but explicit redistribution
rights are unclear or absent. Repackaging one in this repo without per-form
legal review is a license risk. The stand-in is upstream MIT and
redistributable under the same terms as `test_template.hwpx`.

### Live demo policy

**Operators must replace this fixture with the actual program-specific
.hwpx before any live demo.** The `case06` scenario’s
`_GRANT_TABLE_ID` and `_FIELD_ORDER` constants must also be re-mapped to
the real form’s table id and row order, since cell coordinates differ
across forms. The `case06` README and demo script (1-min / 3-min / 5-min)
both call this out so the demo team does not accidentally show the
stand-in to a customer as a "real" govt form.

### Rebuild

```bash
uv run python personas/scripts/build_grant_template.py
```
The script is idempotent: re-runs produce a byte-equivalent .hwpx so the
fixture can be safely regenerated in CI without churn.

## Why a fixture and not the real form

- License sourcing for a specific govt form requires per-form review (issuer,
  publication rights, redistribution clauses) — out of scope for T17.
- A minimal MIT-derivative fixture exercises 100 % of `core/docgen/hwpx.py`
  surface (set_cell, replace_in_cell, extract_text, error paths) without
  blocking on legal review.
