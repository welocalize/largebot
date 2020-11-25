#!/usr/bin/env python3

import typer
import time

from largebot.files import assign_creators, assign_qcs, how_long
from largebot.logger import get_logger

logger = get_logger(__name__)

app = typer.Typer()

@app.command(help='Refresh file assignments for LargeBot Creators.')
def refresh_creators(
        lang: str = typer.Argument('EN-US'),
        phase: str = typer.Argument('_Training'),
        task: str = typer.Argument('Intent'),
        DRY_RUN: bool = typer.Option(False, '--dry-run', '-d')
):
    assign_creators(
        LANG=lang,
        PHASE=phase,
        TASK=task,
        DRY_RUN=DRY_RUN
    )


@app.command(help='Refresh file assignments for LargeBot QCs.')
def refresh_qcs(
        lang: str = typer.Argument('EN-US'),
        phase: str = typer.Argument('_Training'),
        task: str = typer.Argument('Intent'),
        DRY_RUN: bool = typer.Option(False, '--dry-run', '-d')
):
    assign_qcs(
        LANG=lang,
        PHASE=phase,
        TASK=task,
        DRY_RUN=DRY_RUN
    )


@app.command(help='Refresh all LargeBot file assignments.')
def refresh_all(
        lang: str = typer.Argument('EN-US'),
        phase: str = typer.Argument('_Training'),
        task: str = typer.Argument('Intent'),
        DRY_RUN: bool = typer.Option(False, '--dry-run', '-d')
):
    assign_creators(
        LANG=lang,
        PHASE=phase,
        TASK=task,
        DRY_RUN=DRY_RUN
    )
    time.sleep(15)
    assign_qcs(
        LANG=lang,
        PHASE=phase,
        TASK=task,
        DRY_RUN=DRY_RUN
    )


@app.command(help='Refresh relative reference to last time assignments were updated.')
def how_long(
        LANG: str = typer.Argument('EN-US'),
        PHASE: str = typer.Argument('_Training')
):
    how_long(
        LANG=LANG,
        PHASE=PHASE
    )


if __name__ == '__main__':
    app()