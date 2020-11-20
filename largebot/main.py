#!/usr/bin/env python3

import typer

from largebot.files import automate

app = typer.Typer()

@app.command()
def run():
    automate()


if __name__ == '__main__':
    app()