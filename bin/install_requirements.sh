#!/usr/bin/env bash

LK_CONDA_ENV=$1

if [[ -z "$LK_CONDA_ENV" ]]; then
    LK_CONDA_ENV="env"
fi

if ! which conda >/dev/null; then
    echo "error: conda executable found"
    exit 1
fi
if ! source activate ${LK_CONDA_ENV}; then
    echo "error: could not activate conda environment $LK_CONDA_ENV"
    exit 1
fi

echo "installing requirements... "
if ! pip install -r requirements.txt; then
    echo "error: could not install requirements"
    exit 1
fi

echo "installing current logistik version... "
if ! pip install --no-cache --no-deps --upgrade .; then
    echo "error: could not install current logistik version"
    exit 1
fi
