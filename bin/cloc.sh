#!/bin/bash
cloc --fullpath --not-match-d "site|logistik/admin/static|web/node_modules|docs|dist|\.git|\.idea|__pycache__|logistik\.egg-info" .
