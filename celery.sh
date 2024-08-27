#!/bin/sh

celery -A witswin worker -B & celery -A witswin beat -S redbeat.RedBeatScheduler --loglevel=info