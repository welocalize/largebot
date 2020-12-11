from fastapi import FastAPI
from largebot.main import get_resource_status, assign_one

app = FastAPI()


@app.get('/')
def root():
    return {'Hello': 'API'}


@app.get('/resource/{resource_code}')
def get_resource_status(resource_code: str):
    return get_resource_status(resource_code)


@app.post('/resource/{resource_code}')
def assign_one(resource_code: str):
    return assign_one(resource_code)