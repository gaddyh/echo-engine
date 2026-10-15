"""Single-run mapper evaluation: JSON input with a list of provider-neutral messages."""
import argparse
import json
import os
from pathlib import Path
from uuid import uuid4

from dotenv import load_dotenv
from rich.console import Console
from rich.table import Table
from rich.text import Text

from .mapper import OpenAIMapper
from .models import MappingResult, Message
from .pipeline import MappingPipeline
from .resolver import InteractionResolver, InteractionStore


def _plain(value: object) -> Text:
    text = str(value)
    has_rtl = any("\u0590" <= character <= "\u08ff" for character in text)
    return Text(text, justify="right" if has_rtl else None)


def _markdown_cell(value: object) -> str:
    return str(value).replace("|", "\\|").replace("\n", "<br>")


def _markdown_report(result: MappingResult, run_id: str) -> str:
    lines = [
        "# Echo interactions",
        "",
        f"Run ID: `{run_id}`",
        "",
        "| ID | Topic | Participants | Messages | Evidence window | Summary |",
        "|:---|---:|:---|:---|:---|---:|",
    ]
    for interaction in result.interactions:
        evidence_window = (
            f"{interaction.first_evidence_at} → {interaction.last_evidence_at}"
        )
        lines.append(
            "| "
            + " | ".join(
                _markdown_cell(value)
                for value in (
                    interaction.id,
                    interaction.topic,
                    ", ".join(interaction.participants),
                    ", ".join(interaction.message_ids),
                    evidence_window,
                    interaction.summary,
                )
            )
            + " |"
        )
    if result.unassigned_message_ids:
        lines.extend(
            [
                "",
                "**Unassigned messages:** "
                + ", ".join(_markdown_cell(item) for item in result.unassigned_message_ids),
            ]
        )
    if result.unresolved_local_keys:
        lines.extend(
            [
                "",
                "**Unresolved interactions:** "
                + ", ".join(_markdown_cell(item) for item in result.unresolved_local_keys),
            ]
        )
    if result.diagnostics:
        lines.extend(["", "**Diagnostics:** " + "; ".join(result.diagnostics)])
    return "\n".join(lines) + "\n"


def write_report(result: MappingResult, runs_dir: Path = Path("runs")) -> Path:
    run_id = str(uuid4())
    run_dir = runs_dir / run_id
    run_dir.mkdir(parents=True, exist_ok=False)
    report_path = run_dir / "result.md"
    report_path.write_text(_markdown_report(result, run_id), encoding="utf-8")
    return report_path


def print_result(result: MappingResult) -> None:
    table = Table(title="Echo interactions", show_lines=True)
    table.add_column("ID", style="dim", no_wrap=True)
    table.add_column("Topic", style="bold")
    table.add_column("Participants")
    table.add_column("Messages")
    table.add_column("Evidence window")
    table.add_column("Summary", ratio=2)

    for interaction in result.interactions:
        table.add_row(
            _plain(interaction.id),
            _plain(interaction.topic),
            _plain(", ".join(interaction.participants)),
            _plain(", ".join(interaction.message_ids)),
            _plain(f"{interaction.first_evidence_at} → {interaction.last_evidence_at}"),
            _plain(interaction.summary),
        )

    console = Console()
    console.print(table)
    if result.unassigned_message_ids:
        console.print(
            "[yellow]Unassigned messages:[/yellow] "
            + ", ".join(result.unassigned_message_ids)
        )
    if result.unresolved_local_keys:
        console.print(
            "[yellow]Unresolved interactions:[/yellow] "
            + ", ".join(result.unresolved_local_keys)
        )
    if result.diagnostics:
        console.print("[yellow]Diagnostics:[/yellow] " + "; ".join(result.diagnostics))


def main() -> None:
    load_dotenv()
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path, help="JSON array of Message objects")
    parser.add_argument(
        "--model",
        default=os.getenv("LLM_MODEL_NAME", "gpt-4.1-mini"),
        help="OpenAI model (default: LLM_MODEL_NAME or gpt-4.1-mini)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print machine-readable JSON instead of the human-readable table",
    )
    parser.add_argument(
        "--runs-dir",
        type=Path,
        default=Path("runs"),
        help="Directory for per-run Markdown reports (default: runs)",
    )
    args = parser.parse_args()
    messages = [Message.model_validate(m) for m in json.loads(args.input.read_text())]
    result = MappingPipeline(OpenAIMapper(args.model), InteractionResolver(InteractionStore())).run(messages)
    report_path = write_report(result, args.runs_dir)
    if args.json:
        print(result.model_dump_json(indent=2))
        Console(stderr=True).print(f"[dim]Report written to {report_path}[/dim]")
    else:
        print_result(result)
        Console().print(f"[dim]Report written to {report_path}[/dim]")


if __name__ == "__main__":
    main()
