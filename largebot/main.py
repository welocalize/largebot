#!/usr/bin/env python3

import typer
import time

from largebot.files import assign_creators, assign_qcs, how_long
from largebot.largebotter import ResourceBot, ResourceSheet
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
        refresh: bool = typer.Option(False, '--refresh', '-r'),
        DRY_RUN: bool = typer.Option(False, '--dry-run', '-d')
):
    with ResourceBot(
            lang=lang,
            phase=phase,
            dry_run=DRY_RUN
    ) as bot:
        if refresh:
            bot.refresh()
        bot.assign()


@app.command(help='Assign single resource by resource code.')
def assign_one(
        resource_code: str = typer.Argument(...),
        phase: str = typer.Argument('_Training'),
        DRY_RUN: bool = typer.Option(False, '--dry-run', '-d')
):
    lang = f"{resource_code.split('_')[0]}-US"
    bot = ResourceBot(lang=lang, phase=phase, dry_run=DRY_RUN)
    return bot.assign_one(resource_code)


@app.command(help='Get status of single resource by resource code.')
def get_resource_status(
        resource_code: str = typer.Argument(...),
        phase: str = typer.Argument('_Training')
):
    lang = f"{resource_code.split('_')[0]}-US"
    role = 'Creator' if resource_code.split('_')[1] == 'Cr' else 'QC'
    resource_sheet = ResourceSheet(lang=lang, phase=phase, role=role)
    return resource_sheet.get_resource_status(resource_code)


@app.command(help='Refresh relative reference to last time assignments were updated.')
def when(
        lang: str = typer.Argument('EN-US'),
        phase: str = typer.Argument('_Training')
):
    how_long(
        LANG=lang,
        PHASE=phase
    )


if __name__ == '__main__':
    app()