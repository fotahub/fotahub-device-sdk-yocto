#!/usr/bin/env python
import sys
if sys.version_info[0] < 3:
    print('ERROR: This program requires Python 3')
    sys.exit(1)

import fotahubclient.daemon.main as fotahub_daemon

if __name__ == '__main__': 
    sys.exit(fotahub_daemon.main()) 