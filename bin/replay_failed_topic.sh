#!/usr/bin/env bash

source activate $2
LK_ENVIRONMENT=$1 python bin/replay_failed_topic.py
