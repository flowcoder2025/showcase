"""OCR surface — local Gemma VLM (MLX) plus domain-specific extractors.

Public sub-modules:
    - ``gemma``   : :func:`extract`, :func:`warmup`, ``ModelLiteral``
    - ``invoice`` : :func:`extract`, :func:`validate_biznum`,
      :func:`to_accounting_csv`, :class:`InvoiceData`
    - ``receipt`` : :func:`extract`, :class:`ReceiptData`

``_mlx_server`` is an internal subprocess manager and is intentionally not part
of the public surface; importing it directly is unsupported.
"""

from flowcoder_office_tools.ocr import gemma, invoice, receipt

__all__ = ["gemma", "invoice", "receipt"]
