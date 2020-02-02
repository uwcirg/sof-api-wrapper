SMART-on-FHIR Proxy
===================
SMART-on-FHIR confidential client and proxy


Development
-----------
To start the application follow the below steps in the checkout root

Copy default environment variable file and modify as necessary

    cp sof_wrapper.env.default sof_wrapper.env

Build the docker image. Should only be necessary on first run or if dependencies change.

    docker-compose build

Start the container in detached mode

    docker-compose up --detach

Read application logs

    docker-compose logs --follow


License
-------
BSD
