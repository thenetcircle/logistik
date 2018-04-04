Requirements
====

Some package requirements (debian/ubuntu):
    
    $ sudo apt-get update
    $ sudo apt-get install tar git curl nano wget dialog net-tools build-essential
    $ sudo apt-get install libssl-dev libmysqlclient-dev libpq-dev virtualenv

Install [miniconda](https://conda.io/docs/install/quick.html):

    $ wget https://repo.continuum.io/miniconda/Miniconda3-latest-Linux-x86_64.sh
    $ bash Miniconda3-latest-Linux-x86_64.sh # assuming defaults accepted
    $ source ~/.bashrc

Create your environment and install the requirements:

    $ conda create -n recsys python=3.6
    $ source activate logistik
    (logistik) $ cd recsys/
    (logistik) $ pip install -r requirements.txt

Building the documentation
====

Viewing locally:

    $ mkdocs serve

Building the site (not necessary):

    $ mkdocs build
        
Deploy to gihub pages:

    $ mkdocs gh-deploy


