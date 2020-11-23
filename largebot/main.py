#!/usr/bin/env python3

import typer
import time

from largebot.files import assign_creators, assign_qcs
from largebot.logger import get_logger

logger = get_logger(__name__)

app = typer.Typer()

@app.command(help='Refresh file assignments for LargeBot Creators.')
def refresh_creators(
        lang: str = typer.Argument('EN-US'),
        phase: str = typer.Argument('_Training'),
        task: str = typer.Argument('Intent'),
        dry_run: bool = typer.Option(False, '--dry-run', '-d')
):
    assign_creators(
        LANG=lang,
        PHASE=phase,
        TASK=task,
        dry_run=dry_run
    )


@app.command(help='Refresh file assignments for LargeBot QCs.')
def refresh_qcs(
        lang: str = typer.Argument('EN-US'),
        phase: str = typer.Argument('_Training'),
        task: str = typer.Argument('Intent'),
        dry_run: bool = typer.Option(False, '--dry-run', '-d')
):
    assign_qcs(
        LANG=lang,
        PHASE=phase,
        TASK=task,
        dry_run=dry_run
    )


@app.command(help='Refresh all LargeBot file assignments.')
def refresh_all(
        lang: str = typer.Argument('EN-US'),
        phase: str = typer.Argument('_Training'),
        task: str = typer.Argument('Intent'),
        dry_run: bool = typer.Option(False, '--dry-run', '-d')
):
    assign_creators(
        LANG=lang,
        PHASE=phase,
        TASK=task,
        dry_run=dry_run
    )
    time.sleep(15)
    assign_qcs(
        LANG=lang,
        PHASE=phase,
        TASK=task,
        dry_run=dry_run
    )


if __name__ == '__main__':
    app()