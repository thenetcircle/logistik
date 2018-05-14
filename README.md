# Machine Learning Model Logistics

[![Requirements Status](https://requires.io/github/thenetcircle/logistik/requirements.svg?branch=master)](https://requires.io/github/thenetcircle/logistik/requirements/?branch=master)

"90% of the effort in successful machine learning is not about the algorithm or the model or the learning. It’s about logistics."

## Starting the consul agent

```bash
sudo consul agent -config-file /etc/consul.d/config.json
```

## Starting logistik

```bash
LK_ENVIRONMENT=oscar ianitor logistik -- gunicorn --workers 1 --threads 1 --worker-class eventlet -b 0.0.0.0:5656 app:app
```

Note: ianitor hasn't released the PR enabling service-address to be specified, so endpoint needs to be set manually
in logistik's db after registration.