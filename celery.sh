#!/bin/sh

celery -A witswin worker --beat --concurrency 1 -l INFO 