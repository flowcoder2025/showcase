"""시연용 로거 — rich 콘솔 + secrets 마스킹 자동 적용.

Note: filename is `demo_logger.py` (not `logging.py`) to avoid shadowing
stdlib's `logging` module within the `core.common` package.
"""
from rich.console import Console
from rich.markup import escape

from core.common import secrets_mask


class DemoLogger:
    def __init__(self, case_id: str):
        self.case_id = case_id
        self.console = Console()

    def _format(self, level: str, msg: str) -> str:
        # escape() prevents rich from interpreting `[level]` / `[case_id]` as markup tags
        return escape(f"[{level}] [{self.case_id}] {secrets_mask.mask_text(msg)}")

    def info(self, msg: str) -> None:
        self.console.print(self._format("INFO", msg))

    def success(self, msg: str) -> None:
        self.console.print(f"[bold green]{self._format('OK', msg)}[/bold green]")

    def warning(self, msg: str) -> None:
        self.console.print(f"[yellow]{self._format('WARN', msg)}[/yellow]")

    def error(self, msg: str) -> None:
        self.console.print(f"[bold red]{self._format('ERR', msg)}[/bold red]")


def demo_logger(case_id: str) -> DemoLogger:
    return DemoLogger(case_id)
