#!/bin/bash
cloc --fullpath --not-match-d "site|logistik/admin/static|logistik/admin/web|docs|dist|\.git|\.idea|__pycache__|logistik\.egg-info" .
