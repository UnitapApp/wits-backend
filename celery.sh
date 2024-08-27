#!/bin/sh

celery -A witswin worker --beat -l INFO