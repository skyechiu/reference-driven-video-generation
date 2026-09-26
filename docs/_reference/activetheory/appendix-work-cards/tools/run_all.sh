#!/bin/bash
cd "$(dirname "$0")"
K=6 OUT=cap timeout 3000 node capture.js > cap6.log 2>&1; echo "EXIT6 $?" >> status.log
timeout 600 node hover.js > hover.log 2>&1; echo "EXITH $?" >> status.log
K=2 OUT=capk2 timeout 3000 node capture.js > capk2.log 2>&1; echo "EXIT2 $?" >> status.log
