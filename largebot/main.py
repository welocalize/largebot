from fastapi import FastAPI
from largebot.largebotter import ResourceSheet, ResourceBot

app = FastAPI()


@app.get('/')
def root():
    return {'Hello': 'API'}


@app.get('/resource/{resource_code}')
def get_resource_status(
        resource_code: str,
        phase: str = '_Training'
):
    lang = f"{resource_code.split('_')[0]}-US"
    role = 'Creator' if resource_code.split('_')[1] == 'Cr' else 'QC'
    resource_sheet = ResourceSheet(lang=lang, phase=phase, role=role)
    return resource_sheet.get_resource_status(resource_code)


@app.post('/resource/{resource_code}')
def assign_one(
        resource_code: str,
        phase: str = '_Training',
        dry_run: bool = False
):
    lang = f"{resource_code.split('_')[0]}-US"
    bot = ResourceBot(lang=lang, phase=phase, dry_run=dry_run)
    return bot.assign_one(resource_code)


if __name__ == '__main__':
    app()