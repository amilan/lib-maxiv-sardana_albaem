#!/usr/bin/env python

"""Common definitions for AlbaEM# sardana controller."""

from sardana import State

# State Map used to convert device server states into sardana states
ALBAEM_STATE_MAP = {
                    'STATE_ACQUIRING': State.Moving,
                    'STATE_ON': State.On,
                    'STATE_RUNNING': State.Moving
                    }
