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

## grant_application_template.hwpx (deferred to T18)

The real Korean government grant form template needed for case06 (정부지원사업
신청서 자동화 시연) is **not present in this directory**. Sourcing it under an
appropriate license — preferably 대한민국 정부 공공누리 1유형 (출처표시) or
direct permission from the issuing agency — is part of T18 (case06 scenario).

Until then, case06 unit tests use `test_template.hwpx` for the
HwpxEditor round-trip, and the case06 scenario script runs against whatever
template the operator places at `personas/sample_data/forms/grant_application_template.hwpx`.

## Why a fixture and not the real form

- License sourcing for a specific govt form requires per-form review (issuer,
  publication rights, redistribution clauses) — out of scope for T17.
- A minimal MIT-derivative fixture exercises 100 % of `core/docgen/hwpx.py`
  surface (set_cell, replace_in_cell, extract_text, error paths) without
  blocking on legal review.
