SMART-on-FHIR Proxy
===================
SMART-on-FHIR confidential client and proxy

Launch
------
To start an EHR launch follow the below steps

Generate a launch URL in the below form, where `SERVER_NAME` matches the value in `sof_wrapper.env`

http://SERVER_NAME/auth/launch

Enter the above URL as the **App Launch URL** in the [SMART App Launcher](https://launch.smarthealthit.org/)

* Uncheck **Simulate launch within the EHR user interface**
* Select **R2 (DSTU2)** for **FHIR Version**

Click **Launch App!**

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


Test
----
Without a ``setup.py`` to install, invoke as follows from the root directory to
automatically include the current directory in ``PYTHONPATH``

    python -m pytest tests

License
-------
BSD
