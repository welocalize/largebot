import typer

from largebot import how_long, ResourceBot, ResourceSheet, TeamsMessage
from largebot.logger import get_logger

logger = get_logger(__name__)

cli = typer.Typer()


@cli.command(help='Refresh all LargeBot file assignments.')
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
        logger.info("Assigning QCs.")
        bot.assign_qcs()
        logger.info("Assigning Creators.")
        bot.assign_creators()


@cli.command(help='Refresh all LargeBot file assignments.')
def refresh_qcs(
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
        logger.info("Assigning QCs.")
        bot.assign_qcs()


@cli.command(help='Refresh all LargeBot file assignments.')
def refresh_creators(
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
        logger.info("Assigning Creators.")
        bot.assign_creators()


@cli.command(help='Assign single resource by resource code.')
def assign_one(
        resource_code: str = typer.Argument(...),
        phase: str = typer.Argument('_Training'),
        DRY_RUN: bool = typer.Option(False, '--dry-run', '-d')
):
    lang = f"{resource_code.split('_')[0]}-US"
    bot = ResourceBot(lang=lang, phase=phase, dry_run=DRY_RUN)
    return bot.assign_one(resource_code)


@cli.command(help='Send Teams Message with summary stats for a given task/role.')
def teams_summary(
        task: str = typer.Argument('Utterance'),
        role: str = typer.Argument('Creator'),
        lang: str = typer.Argument('EN-US'),
        phase: str = typer.Argument('_Training')
):
    update = TeamsMessage(
        task=task,
        role=role,
        lang=lang,
        phase=phase
    )
    update.send()


@cli.command(help='Get status of single resource by resource code.')
def get_resource_status(
        resource_code: str = typer.Argument(...),
        phase: str = typer.Argument('_Training')
):
    lang = f"{resource_code.split('_')[0]}-US"
    role = 'Creator' if resource_code.split('_')[1] == 'Cr' else 'QC'
    resource_sheet = ResourceSheet(lang=lang, phase=phase, role=role)
    return resource_sheet.get_resource_status(resource_code)


@cli.command(help='Refresh relative reference to last time assignments were updated.')
def when(
        lang: str = typer.Argument('EN-US'),
        phase: str = typer.Argument('_Training')
):
    how_long(
        LANG=lang,
        PHASE=phase
    )


if __name__ == '__main__':
    cli()
