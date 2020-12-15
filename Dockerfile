FROM tiangolo/uvicorn-gunicorn-fastapi:python3.8

RUN ls /usr/local/lib/python3.8/site-packages

# RUN curl -L https://raw.githubusercontent.com/pyenv/pyenv-installer/master/bin/pyenv-installer \
#    | bash

# ENV PATH=$HOME/.pyenv/bin:/root/.pyenv/bin:$PATH

ENV PATH=/opt/poetry/bin:$PATH

ENV welo365_client_id="37aba2ba-24ac-4a9b-9553-15967ff85768"

ENV welo365_client_secret="IO53Ev.b0T.D9_t00Hd7tsijl.GR7-u-3_"

RUN mkdir -p /root/Logs/largebot

# RUN git clone git://github.com/pyenv/pyenv.git /tmp/pyenv && \
#     cd /tmp/pyenv/plugins/python-build && \
#     ./install.sh && \
#     rm -rf /tmp/pyenv

RUN curl -sSL https://raw.githubusercontent.com/python-poetry/poetry/master/get-poetry.py | POETRY_HOME=/opt/poetry python && \
    cd /usr/local/bin && \
    ln -s /opt/poetry/bin/poetry && \
    poetry config virtualenvs.create true

# Copy using poetry.lock* in case it doesn't exist yet
COPY ./pyproject.toml ./poetry.lock* /largebot/

COPY ./o365_token.txt /root/

# RUN pyenv install 3.8-dev && pyenv global 3.8-dev

# RUN cd /largebot && poetry env use $( pyenv which python ) && poetry install --no-root --no-dev

RUN cd /largebot && poetry install --no-root --no-dev

COPY . /largebot

WORKDIR /largebot

CMD ["poetry", "run", "uvicorn", "largebot.main:app", "--host", "0.0.0.0", "--port", "80"]

# CMD ["poetry", "run", "uvicorn", "largebot.main:app"]
