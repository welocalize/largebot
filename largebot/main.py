from fastapi import FastAPI

from largebot.largebotter import ResourceSheet, ResourceBot, FileBook

app = FastAPI()


@app.post('/resources/refresh-all')
def refresh_all(
        lang: str = 'EN-US',
        phase: str = '_Training',
        refresh: bool = False,
        dry_run: bool = False
):
    with ResourceBot(
            lang=lang,
            phase=phase,
            dry_run=dry_run
    ) as bot:
        if refresh:
            bot.refresh()
        updates = bot.assign()
    return updates


@app.get('/resource/{resource_code}')
def get_resource_status(
        resource_code: str,
        phase: str = '_Training'
):
    lang = f"{resource_code.split('_')[0]}-US"
    role = 'Creator' if resource_code.split('_')[1] == 'Cr' else 'QC'
    resource_sheet = ResourceSheet(lang=lang, phase=phase, role=role)
    return resource_sheet.get_resource_status(resource_code)


@app.post('/resource/{resource_code}/assign')
def assign_one(
        resource_code: str,
        phase: str = '_Training',
        dry_run: bool = False
):
    lang = f"{resource_code.split('_')[0]}-US"
    bot = ResourceBot(lang=lang, phase=phase, dry_run=dry_run)
    return bot.assign_one(resource_code)


@app.get('/task/{task}/role/{role}')
def get_file_summary(
        task: str,
        role: str,
        lang: str = 'EN-US',
        phase: str = '_Training'
):
    book = FileBook(lang=lang, phase=phase)
    file_sheet = getattr(book, f"{task}{role}")
    status = file_sheet.summary()
    columns = status.index.tolist()
    domains = status.columns.tolist()
    values = status.values.tolist()
    return {
        domains[i]: dict(
            zip(
                columns, _values
            )
        )
        for i, _values in enumerate(values)
    }


if __name__ == '__main__':
    app()
