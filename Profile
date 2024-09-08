web: gunicorn application:application --workers=4 --worker-class=uvicorn.workers.UvicornWorker
