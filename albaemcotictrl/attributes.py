#!/usr/bin/env python

"""Attributes definition for AlbaEM# sardana controller."""

from sardana import DataAccess
from sardana.pool.controller import NotMemorized  # MemorizedNoInit,
from sardana.pool.controller import MaxDimSize  # Memorized,

from sardana.pool.controller import Type, Description, Memorize  # DefaultValue
from sardana.pool.controller import Access, FGet, FSet

# Extra attributes definition
EXTRA_ATTRIBUTES = {
                    "Range": {
                            Type: str,
                            Description: 'Range for the channel',
                            Memorize: NotMemorized,
                            Access: DataAccess.ReadWrite,
                            FGet: 'getRange',
                            FSet: 'setRange'
                            },
                    "Filter": {
                            Type: str,
                            Description: 'Filter for the channel',
                            Memorize: NotMemorized,
                            Access: DataAccess.ReadWrite,
                            FGet: 'getFilter',
                            FSet: 'setFilter'
                            },
                    "Inversion": {
                            Type: str,
                            Description: 'Channel Digital inversion',
                            Memorize: NotMemorized,
                            Access: DataAccess.ReadWrite,
                            FGet: 'getInversion',
                            FSet: 'setInversion'
                            },
                    # "Offset": {
                    #         Type: float,
                    #         Description: 'Offset in % for the channel',
                    #         Memorize: NotMemorized,
                    #         Access: DataAccess.ReadWrite,
                    #         FGet: 'getOffset',
                    #         FSet: 'setOffset'
                    #         },
                    # "SampleRate": {
                    #         Type: float,
                    #         Description: 'Albaem sample rate',
                    #         Memorize: NotMemorized,
                    #         Access: DataAccess.ReadWrite,
                    #         FGet: 'getSampleRate',
                    #         FSet: 'setSampleRate'
                    #         },
                    # "AutoRange": {
                    #         Type: bool,
                    #         Description: 'Enable/Disable EM autorange',
                    #         Memorize: NotMemorized,
                    #         Access: DataAccess.ReadWrite,
                    #         FGet: 'getAutoRange',
                    #         FSet: 'setAutoRange'
                    #         },
                    # attributes added for continuous acqusition mode
                    "NrOfTriggers": {
                            Type: int,
                            Description: 'Nr of triggers',
                            Memorize: NotMemorized,
                            Access: DataAccess.ReadOnly,
                            FGet: 'getNrOfTriggers',
                            FSet: 'setNrOfTriggers'
                            },
                    # "SamplingFrequency": {
                    #         Type: float,
                    #         Description: 'Sampling frequency',
                    #         Memorize: NotMemorized,
                    #         Access: DataAccess.ReadWrite,
                    #         FGet: 'getSamplingFrequency',
                    #         FSet: 'setSamplingFrequency'
                    #         },
                    # "AcquisitionTime": {
                    #         Type: float,
                    #         Description: 'Acquisition time per trigger',
                    #         Memorize: NotMemorized,
                    #         Access: DataAccess.ReadWrite,
                    #         FGet: 'getAcquisitionTime',
                    #         FSet: 'setAcquisitionTime'
                    #         },
                    "TriggerMode": {
                            Type: str,
                            Description: 'Trigger mode: soft or gate',
                            Memorize: NotMemorized,
                            Access: DataAccess.ReadWrite,
                            FGet: 'getTriggerMode',
                            FSet: 'setTriggerMode'
                            },
                    "Data": {
                            Type: [float],
                            Description: 'Data array',
                            Memorize: NotMemorized,
                            Access: DataAccess.ReadOnly,
                            MaxDimSize: (1000000,),
                            FGet: 'getData'
                            }
                         }
