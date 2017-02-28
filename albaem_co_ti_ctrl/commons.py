#!/usr/bin/env python

"""Common definitions for AlbaEM# sardana controller."""

from PyTango import DevState

ALBAEM_STATE_MAP = {
                    'RUNNING': 'MOVING',
                    'ON': 'ON',
                    'IDLE': 'ON'
                    }
