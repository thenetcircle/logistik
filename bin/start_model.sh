#!/bin/bash
ianitor -v \
  --id $(uuidgen | cut -c 1-8) \
  --address 10.60.1.125 \
  --consul-agent=10.60.1.124 \
  --tags logistik \
  --tags model=model \
  --tags node=3 \
  --tags hostname=mk2 \
  --tags version=$(git describe) \
  --port 5052 the_service_name -- \
gunicorn --worker-class eventlet --workers 1 --threads 1 --worker-connections 500 --timeout 180 --bind 0.0.0.0:5053 app:app
