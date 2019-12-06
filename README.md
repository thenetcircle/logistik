# Machine Learning Model Logistics

[![Requirements Status](https://requires.io/github/thenetcircle/logistik/requirements.svg?branch=master)](https://requires.io/github/thenetcircle/logistik/requirements/?branch=master)
[![Build Status](https://travis-ci.org/thenetcircle/logistik.svg?branch=master)](https://travis-ci.org/thenetcircle/logistik)
[![coverage](https://codecov.io/gh/thenetcircle/logistik/branch/master/graph/badge.svg)](https://codecov.io/gh/thenetcircle/logistik)
[![Code Climate](https://codeclimate.com/github/thenetcircle/logistik/badges/gpa.svg)](https://codeclimate.com/github/thenetcircle/logistik)
[![License](https://img.shields.io/github/license/thenetcircle/logistik.svg)](LICENSE)

"90% of the effort in successful machine learning is not about the algorithm or the model or the learning. It’s about logistics."

![Flow](docs/workflow-for-recs.png)

<a href="docs/diagram.png"><img src="docs/diagram.png" width="570" alt="Diagram"></a>

## Starting the consul agent

```bash
sudo consul agent -config-file /etc/consul.d/config.json
```

## Starting logistik

```bash
LK_ENVIRONMENT=default gunicorn \
  --workers 1 \
  --threads 1 \
  --worker-class eventlet \
  --bind 0.0.0.0:5656 app:app
```

## Starting a model

Either register your model manually in Consul, or use a wrapper like `ianitor` to do it for you.

```bash
#!/bin/bash
ianitor -v \
  --id the_service_name_5052 \  # needs to be unique
  --address 10.60.1.125 \  # address to this node
  --consul-agent=10.60.1.124 \  # which consul agent to connect to
  --tags logistik \  # this is needed for logistik to not ignore your service in consul
  --tags model=model \  # usually one of ['model', 'canary', 'deploy']
  --tags node=3 \  # the instance number for this model on this host, if you run more than one
  --tags hostname=mk2 \  # human-readable identifier for this host
  --tags version=$(git describe) \  # usually the version of your model, using the git tag here
  --port 5052 \
  the_service_name -- \  # you should name your service here, likely the name of your model
gunicorn \  # this is whatever command is used to start your model, here we're using gunicorn
  --worker-class eventlet \
  --workers 1 \
  --threads 1 \
  --name the_service_name \
  --worker-connections 50 \
  --timeout 240 \
  --bind 0.0.0.0:5053 \
  app:app
```

If you use uWSGI instead of Gunicorn and exposes a http stats server, logistik will make use of it in the Web UI 
(assuming the stats server is running on 100 port numbers higher than the model bind port):

```bash
#!/bin/bash
ianitor -v \
  --id the_service_name_5052 \  # needs to be unique
  --address 10.60.1.125 \  # address to this node
  --consul-agent=10.60.1.124 \  # which consul agent to connect to
  --tags logistik \  # this is needed for logistik to not ignore your service in consul
  --tags model=model \  # usually one of ['model', 'canary', 'deploy']
  --tags node=3 \  # the instance number for this model on this host, if you run more than one
  --tags hostname=mk2 \  # human-readable identifier for this host
  --tags version=$(git describe) \  # usually the version of your model, using the git tag here
  --port 5052 \
  the_service_name -- \  # you should name your service here, likely the name of your model
uwsgi \
  --worker-reload-mercy 600 \
  --http-socket 0.0.0.0:5053 \
  --wsgi-file detect.py \
  --master \
  --processes 1 \
  --threads 1 \
  --stats 0.0.0.0:5153 \
  --callable app
```

Statistics in the Web UI:

<a href="docs/stats.png"><img src="docs/stats.png" width="570" alt="Model statistics"></a>
