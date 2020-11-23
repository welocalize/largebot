#!/usr/bin/env python3

import typer
import time

from largebot.files import assign_creators, assign_qcs

app = typer.Typer()

@app.command(help='Refresh file assignments for LargeBot Creators.')
def refresh_creators(
        lang: str = typer.Argument('EN-US'),
        phase: str = typer.Argument('_Training'),
        task: str = typer.Argument('Intent')
):
    assign_creators(
        LANG=lang,
        PHASE=phase,
        TASK=task
    )


@app.command(help='Refresh file assignments for LargeBot QCs.')
def refresh_qcs(
        lang: str = typer.Argument('EN-US'),
        phase: str = typer.Argument('_Training'),
        task: str = typer.Argument('Intent')
):
    assign_qcs(
        LANG=lang,
        PHASE=phase,
        TASK=task
    )


@app.command(help='Refresh all LargeBot file assignments.')
def refresh_all(
        lang: str = typer.Argument('EN-US'),
        phase: str = typer.Argument('_Training'),
        task: str = typer.Argument('Intent')
):
    assign_creators(
        LANG=lang,
        PHASE=phase,
        TASK=task
    )
    time.sleep(15)
    assign_qcs(
        LANG=lang,
        PHASE=phase,
        TASK=task
    )


if __name__ == '__main__':
    app()