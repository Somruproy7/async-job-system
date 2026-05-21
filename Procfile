api: uvicorn app.main:app --host 0.0.0.0 --port $PORT
worker: celery -A app.core.celery_app.celery_app worker --queues=high,default,low --concurrency=4 --loglevel=info
beat: celery -A app.core.celery_app.celery_app beat --loglevel=info
flower: celery -A app.core.celery_app.celery_app flower --port=$PORT --basic_auth=admin:flowerpass
