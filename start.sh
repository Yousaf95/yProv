#!/bin/bash

./../usr/bin/neo4j-admin dbms set-initial-password $PASSWORD
./../usr/bin/neo4j console&

status_code=$(curl -o /dev/null -s -w "%{http_code}\n" http://localhost:7474/)
while [ $status_code -ne 200 ]; do
    status_code=$(curl -o /dev/null -s -w "%{http_code}\n" http://localhost:7474/)
done

python ./app.py