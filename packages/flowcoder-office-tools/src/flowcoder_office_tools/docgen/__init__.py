"""Document generation surface — HWPX forms, PDFs, Word, Jinja templates.

Public sub-modules:
    - ``hwp_preview`` : :func:`render_preview`
    - ``hwpx``        : :func:`fill_form`, :func:`extract_text`
    - ``pdf``         : :func:`md_to_pdf`, :class:`MdToPdfError`
    - ``template``    : :func:`render_string`, :func:`render_file`,
      :func:`render_html_string`, :func:`render_html_file`
    - ``word``        : :func:`build_quote`
"""

from flowcoder_office_tools.docgen import hwp_preview, hwpx, pdf, template, word

__all__ = ["hwp_preview", "hwpx", "pdf", "template", "word"]
