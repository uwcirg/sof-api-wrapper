FROM python:3.7

WORKDIR /opt/app

ARG VERSION_STRING
ENV VERSION_STRING=$VERSION_STRING

COPY requirements.txt .
RUN pip install --requirement requirements.txt

COPY . .

EXPOSE 5000

ENV FLASK_APP=sof_wrapper/app:create_app() \
    FLASK_ENV=development

CMD flask run --host 0.0.0.0
