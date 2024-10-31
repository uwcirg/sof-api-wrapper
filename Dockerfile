FROM python:3.7

WORKDIR /opt/app

ARG VERSION_STRING
ENV VERSION_STRING=$VERSION_STRING

COPY requirements.txt .
RUN pip install --requirement requirements.txt

COPY . .

ENV FLASK_APP=sof_wrapper.app:create_app() \
    PORT=8000

EXPOSE "${PORT}"

CMD gunicorn --workers=5 --bind "0.0.0.0:${PORT:-8000}" ${FLASK_APP}
