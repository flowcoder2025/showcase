"""Excel manipulation surface — readers, mergers, pivots, writers, validators.

Public sub-modules:
    - ``reader``    : :func:`read_dir`
    - ``merger``    : :func:`merge_by_vendor`
    - ``pivot``     : :func:`vendor_by_month`
    - ``writer``    : :func:`write_styled_report`
    - ``validator`` : :func:`detect_unit_price_outliers`
"""

from flowcoder_office_tools.excel import merger, pivot, reader, validator, writer

__all__ = ["merger", "pivot", "reader", "validator", "writer"]
