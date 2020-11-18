#!/usr/bin/env python3

import typer

from largebot.files import automate

app = typer.Typer()

@app.command()
def run(
        lang: str = typer.Argument(...),
        domain: str = typer.Argument(...),
        task: str = typer.Argument(...),
        phase: str = typer.Argument(...)
):
    automate(
        LANG=lang,
        DOMAIN=domain,
        TASK=task,
        PROJ_PHASE=phase
    )


if __name__ == '__main__':
    app()