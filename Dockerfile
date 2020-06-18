FROM python:3.7

WORKDIR /opt/app

COPY requirements.txt .
RUN pip install --requirement requirements.txt

COPY . .

EXPOSE 5000

ENV FLASK_APP=sof_wrapper/wsgi:application \
    FLASK_ENV=development

CMD flask run --host 0.0.0.0
