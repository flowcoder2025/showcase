"""Build ``grant_application_template.hwpx`` test fixture.

Take the upstream Skeleton-derived ``test_template.hwpx`` (3-row × 2-col table,
id=999000001) and replace its ``<hp:tbl>`` element with an 8-row × 2-col table
whose left column carries Korean grant-application labels and whose right
column is empty (HwpxEditor will fill those at scenario runtime).

The result is repacked into a fresh .hwpx zip beside the source under
``personas/sample_data/forms/grant_application_template.hwpx``.

Why a stand-in (and not a real govt form): real TIPA / SMTECH / K-Startup
forms have implicit "applicant use" license but redistribution rights are
unclear. Repackaging one in this repo without per-form review is a license
risk. The stand-in mimics the shape of a typical grant application so the
case06 scenario exercises ``hwpx.fill_form`` end-to-end. Live demos must
swap in the actual program-specific .hwpx — see ``forms/LICENSE.md``.

This script is **idempotent**: running it repeatedly produces a byte-for-byte
identical output (same table id, same labels, deterministic zip ordering).

Usage:
    uv run python personas/scripts/build_grant_template.py
"""

from __future__ import annotations

import re
import zipfile
from pathlib import Path

# table id chosen distinct from test_template (999000001) to avoid confusion.
GRANT_TABLE_ID = "999000002"

# 8 (label, initial_value) pairs — left col labels, right col placeholder.
# Order must match GrantApplication TypedDict so scenario can map by row index.
GRANT_LABELS: tuple[tuple[str, str], ...] = (
    ("회사명", ""),
    ("대표자명", ""),
    ("사업자등록번호", ""),
    ("사업분야", ""),
    ("신청금액", ""),
    ("매출액", ""),
    ("직원수", ""),
    ("신청일자", ""),
)

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SOURCE = REPO_ROOT / "personas" / "sample_data" / "forms" / "test_template.hwpx"
OUT = REPO_ROOT / "personas" / "sample_data" / "forms" / "grant_application_template.hwpx"


def _build_cell_xml(*, col_addr: int, row_addr: int, text: str) -> str:
    """Render a single ``<hp:tc>`` cell. Mirrors structure from test_template."""
    return (
        '<hp:tc name="" header="0" hasMargin="0" protect="0" editable="0" '
        'dirty="0" borderFillIDRef="1">'
        '<hp:subList id="" textDirection="HORIZONTAL" lineWrap="BREAK" '
        'vertAlign="TOP" linkListIDRef="0" linkListNextIDRef="0" '
        'textWidth="0" textHeight="0" hasTextRef="0" hasNumRef="0">'
        '<hp:p id="0" paraPrIDRef="0" styleIDRef="0" pageBreak="0" '
        'columnBreak="0" merged="0">'
        '<hp:run charPrIDRef="0">'
        f"<hp:t>{text}</hp:t>"
        "</hp:run></hp:p></hp:subList>"
        f'<hp:cellAddr colAddr="{col_addr}" rowAddr="{row_addr}"/>'
        '<hp:cellSpan colSpan="1" rowSpan="1"/>'
        '<hp:cellSz width="5000" height="1000"/>'
        '<hp:cellMargin left="510" right="510" top="141" bottom="141"/>'
        "</hp:tc>"
    )


def _build_table_xml() -> str:
    """Render the full ``<hp:tbl id="GRANT_TABLE_ID">`` 8×2 table element."""
    rows: list[str] = []
    for row_idx, (label, value) in enumerate(GRANT_LABELS):
        left = _build_cell_xml(col_addr=0, row_addr=row_idx, text=label)
        right = _build_cell_xml(col_addr=1, row_addr=row_idx, text=value)
        rows.append(f"<hp:tr>{left}{right}</hp:tr>")
    row_xml = "".join(rows)
    return (
        f'<hp:tbl id="{GRANT_TABLE_ID}" zOrder="0" numberingType="TABLE" '
        'textWrap="TOP_AND_BOTTOM" textFlow="BOTH_SIDES" lock="0" '
        'dropcapstyle="None" pageBreak="CELL" repeatHeader="1" '
        f'rowCnt="{len(GRANT_LABELS)}" colCnt="2" cellSpacing="0" '
        'borderFillIDRef="1" noAdjust="0">'
        '<hp:sz width="10000" widthRelTo="ABSOLUTE" '
        f'height="{len(GRANT_LABELS) * 1000}" heightRelTo="ABSOLUTE" protect="0"/>'
        '<hp:pos treatAsChar="1" affectLSpacing="0" flowWithText="1" '
        'allowOverlap="0" holdAnchorAndSO="0" vertRelTo="PARA" '
        'horzRelTo="COLUMN" vertAlign="TOP" horzAlign="LEFT" '
        'vertOffset="0" horzOffset="0"/>'
        '<hp:outMargin left="283" right="283" top="283" bottom="283"/>'
        '<hp:inMargin left="510" right="510" top="141" bottom="141"/>'
        f"{row_xml}"
        "</hp:tbl>"
    )


def _splice_section_xml(original: str) -> str:
    """Replace the existing ``<hp:tbl ...>...</hp:tbl>`` block in section0.xml."""
    new_tbl = _build_table_xml()
    pattern = re.compile(r"<hp:tbl\s[^>]*?>.*?</hp:tbl>", re.DOTALL)
    if not pattern.search(original):
        raise RuntimeError("source section0.xml has no <hp:tbl> — cannot splice grant table")
    return pattern.sub(new_tbl, original, count=1)


def build(*, source: Path = SOURCE, out: Path = OUT) -> Path:
    """Build the grant template and return its path. Overwrites if present."""
    if not source.exists():
        raise FileNotFoundError(f"source template missing: {source}")

    out.parent.mkdir(parents=True, exist_ok=True)

    # Read all entries from the source zip and rewrite section0.xml.
    with zipfile.ZipFile(source) as zin:
        names = zin.namelist()
        contents: dict[str, bytes] = {n: zin.read(n) for n in names}

    section_key = "Contents/section0.xml"
    if section_key not in contents:
        raise RuntimeError(f"source HWPX missing {section_key}")
    section_text = contents[section_key].decode("utf-8")
    contents[section_key] = _splice_section_xml(section_text).encode("utf-8")

    # Write a fresh zip — deterministic order = source order; mimetype must be
    # the first entry and stored uncompressed for HWPX recognition.
    if out.exists():
        out.unlink()
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zout:
        # mimetype first, uncompressed (HWPX spec).
        if "mimetype" in contents:
            info = zipfile.ZipInfo("mimetype")
            info.compress_type = zipfile.ZIP_STORED
            zout.writestr(info, contents["mimetype"])
        for name in names:
            if name == "mimetype":
                continue
            zout.writestr(name, contents[name])
    return out


def main() -> None:
    target = build()
    print(f"wrote {target} ({target.stat().st_size:,} bytes)")
    # Sanity: ensure zip still round-trips.
    with zipfile.ZipFile(target) as zf:
        assert "Contents/section0.xml" in zf.namelist()
        body = zf.read("Contents/section0.xml").decode("utf-8")
        assert f'id="{GRANT_TABLE_ID}"' in body
        for label, _ in GRANT_LABELS:
            assert f"<hp:t>{label}</hp:t>" in body, f"label not embedded: {label}"
    print(f"verified: table id={GRANT_TABLE_ID}, {len(GRANT_LABELS)} labels")


if __name__ == "__main__":  # pragma: no cover - script entry
    main()
