#!/usr/bin/env python

from setuptools import setup, find_packages


version = '0.1.0'

setup(
    name='logistik',
    version=version,
    description="ML Logistics",
    long_description="""Machine learning logistics system.""",
    classifiers=[],
    author='Service Team @ TNC',
    author_email='contact@thenetcircle.com',
    url='https://github.com/thenetcircle/logistik',
    license='MIT',
    packages=find_packages(exclude=['ez_setup', 'examples', 'tests']),
    include_package_data=True,
    zip_safe=False,
    install_requires=[
        'pyyaml',
        'redis',
        'eventlet',
        'ianitor',
        'psycopg2-binary',
        'sqlalchemy',
        'flask-restful',
        'flask-sqlalchemy',
        'Flask-Testing',
        'flask-oauthlib',
        'gunicorn',
        'codecov',
        'fakeredis',
        'nose',
        'codecov',
        'coverage',
        'kombu',
        'typing',
        'nose-parameterized',
        'python-consul',
        'python-dateutil',
        'psycogreen',
        'statsd',
        'pymitter',
        'gitpython',
        'raven',
        'kafka-python',
        'activitystreams',
        'yapsy',
    ])
