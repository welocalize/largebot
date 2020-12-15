from fastapi import FastAPI, Form
from fastapi.staticfiles import StaticFiles
import requests

from largebot.logger import get_logger
from largebot.largebotter import ResourceSheet, ResourceBot, FileBook

logger = get_logger(__name__)

app = FastAPI()

app.mount('/static', StaticFiles(directory='static'), name='static')

@app.post('/resource/')
async def get_resource(
        lang: str = Form(...),
        role: str = Form(...),
        resource_number: int = Form(...),
        phase: str = Form(...)
):
    resource_code = f"{lang[:2]}_{role[:2]}_{resource_number:02d}"
    resource_sheet = ResourceSheet(lang=lang, phase=phase, role=role)
    return resource_sheet.get_resource_status(resource_code)


@app.post('/assign/')
async def assign_resource(
        lang: str = Form(...),
        role: str = Form(...),
        resource_number: int = Form(...),
        phase: str = Form(...),
        dry_run: str = Form('')
):
    resource_code = f"{lang[:2]}_{role[:2]}_{resource_number:02d}"
    dry_run = bool(dry_run == 'dry_run')
    bot = ResourceBot(lang=lang, phase=phase, dry_run=dry_run)
    return bot.assign_one(resource_code)


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


@app.get('/resource/{resource_code}', name='get_resource_by_code')
def get_resource_status(
        resource_code: str,
        phase: str = '_Training'
):
    lang = f"{resource_code.split('_')[0]}-US"
    role = 'Creator' if resource_code.split('_')[1] == 'Cr' else 'QC'
    resource_sheet = ResourceSheet(lang=lang, phase=phase, role=role)
    return resource_sheet.get_resource_status(resource_code)


@app.get('/resource/{resource_code}/assign')
def assign_one(
        resource_code: str,
        phase: str = '_Training',
        dry_run: bool = False
):
    lang = f"{resource_code.split('_')[0]}-US"
    bot = ResourceBot(lang=lang, phase=phase, dry_run=dry_run)
    return bot.assign_one(resource_code)


@app.get('/task/{task}/role/{role}/summary')
def get_file_summary(
        task: str,
        role: str,
        lang: str = 'EN-US',
        phase: str = '_Training'
):
    book = FileBook(lang=lang, phase=phase)
    file_sheet = getattr(book, f"{task}{role}")
    summary = file_sheet.summary()
    columns = summary.index.tolist()
    domains = summary.columns.tolist()
    return {
        domain: {
            status: count
            for status in columns
            if (count := str(summary[domain][status]))
        }
        for domain in domains
    }


if __name__ == '__main__':
    app()
