FROM pypy:3.10

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Set work directory
WORKDIR /usr/src/app

RUN apt update && apt install gcc


# RUN apt-get update && \
#     apt-get install -y --no-install-recommends \
#     build-essential \
#     gcc \
#     libpq-dev \
#     libc-dev \
#     netcat-traditional \
#     && apt-get clean && \
#     rm -rf /var/lib/apt/lists/*


RUN pip install --upgrade pip
COPY ./requirements.txt .
RUN pip install -r requirements.txt

RUN ln -s /usr/local/bin/pypy3 /usr/local/bin/python


# Copy project
COPY ./src .
COPY ./start.sh .
COPY ./celery.sh .


RUN pypy3 manage.py collectstatic --noinput
