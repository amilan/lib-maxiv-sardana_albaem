#!/usr/bin/env python

"""Sardana Controller for the AlbaEM#."""

# import logging
import PyTango


# from sardana import pool
# from sardana.pool import PoolUtil
from sardana.pool.controller import CounterTimerController
from sardana.pool import AcqTriggerType
from sardana.pool.controller import NotMemorized  # MemorizedNoInit,
from sardana.pool.controller import MaxDimSize  # Memorized,

from .commons import ALBAEM_STATE_MAP


class AlbaemCoTiCtrl(CounterTimerController):
    """
    Sardana CounterTimer controller for the Alba Electrometer.

    The only way to use this controller is to define up to 5 channels
    and create a measurement group where the first channel is a master channel.
    The Adlink card works in a way where acquisition for all channels is
    started only once and in controller this is done when StartsAll() method
    was called for this controller, only when PreStartOne() was called for
    master channel.

    Configuration of Albaem is done in LoadOne() method where size of
    acquisition buffer is calculated from acquisition time and SampleRate
    property.

    Value returned by a channel is an average of buffer values.
    """

    MaxDevice = 5
    class_prop = {'Albaemname': {'Description': 'Albaem DS name',
                                 'Type': 'PyTango.DevString'},
                  }

    ctrl_extra_attributes = {"Range": {
                                'Type': 'PyTango.DevString',
                                'Description': 'Range for the channel',
                                'memorized': NotMemorized,
                                'R/W Type': 'PyTango.READ_WRITE'
                                },
                             "Filter": {
                                'Type': 'PyTango.DevString',
                                'Description': 'Filter for the channel',
                                'memorized': NotMemorized,
                                'R/W Type': 'PyTango.READ_WRITE'
                                },
                             "DInversion": {
                                'Type': 'PyTango.DevString',
                                'Description': 'Channel Digital inversion',
                                'memorized': NotMemorized,
                                'R/W Type': 'PyTango.READ_WRITE'
                                },
                             "Offset": {
                                'Type': 'PyTango.DevDouble',
                                'Description': 'Offset in % for the channel',
                                'memorized': NotMemorized,
                                'R/W Type': 'PyTango.READ_WRITE'
                                },
                             "SampleRate": {
                                'Type': 'PyTango.DevDouble',
                                'Description': 'Albaem sample rate',
                                'memorized': NotMemorized,
                                'R/W Type': 'PyTango.READ_WRITE'
                                },
                             "AutoRange": {
                                'Type': 'PyTango.DevBoolean',
                                'Description': 'Enable/Disable electrometer autorange',
                                'memorized': NotMemorized,
                                'R/W Type': 'PyTango.READ_WRITE'
                                },
                             # attributes added for continuous acqusition mode
                             "NrOfTriggers": {
                                'Type': 'PyTango.DevLong',
                                'Description': 'Nr of triggers',
                                'memorized': NotMemorized,
                                'R/W Type': 'PyTango.READ_WRITE'
                                },
                             "SamplingFrequency": {
                                'Type': 'PyTango.DevDouble',
                                'Description': 'Sampling frequency',
                                'memorized': NotMemorized,
                                'R/W Type': 'PyTango.READ_WRITE'
                                },
                             "AcquisitionTime": {
                                'Type': 'PyTango.DevDouble',
                                'Description': 'Acquisition time per trigger',
                                'memorized': NotMemorized,
                                'R/W Type': 'PyTango.READ_WRITE'
                                },
                             "TriggerMode": {
                                'Type': 'PyTango.DevString',
                                'Description': 'Trigger mode: soft or gate',
                                'memorized': NotMemorized,
                                'R/W Type': 'PyTango.READ_WRITE'
                                },
                             "Data": {
                                'Type': [float],
                                'Description': 'Trigger mode: soft or gate',
                                'memorized': NotMemorized,
                                'R/W Type': 'PyTango.READ',
                                MaxDimSize: (1000000,)
                                }
                             }

    def __init__(self, inst, props, *args, **kwargs):
        """Class initialization."""
        # self._log.setLevel(logging.DEBUG)
        CounterTimerController.__init__(self, inst, props, *args, **kwargs)
        # self._log.setLevel(logging.INFO)
        self._log.debug("__init__(%s, %s): Entering...",
                        repr(inst), repr(props))

        self._master = None
        self._integration_time = 0.0
        self.avSamplesMax = 1000

        # NOTE: Not sure that this is needed ...
        self._channels = []

        # TODO: this is not a good idea, better change it. Maybe avoid ReadAll?
        # TODO: Refactor the initialization of self._measures
        # self._measures = ['0', '0', '0', '0']
        self._measures = []

        self.lastvalues = []
        self.contAcqChannels = {}
        self.acqchannels = []
        self.state = None
        # TODO: Refactor the following lists
        self.ranges = ['', '', '', '']
        self.filters = ['', '', '', '']
        self.dinversions = ['', '', '', '']
        self.offsets = ['', '', '', '']

        self.sampleRate = 0.0
        try:
            self.AemDevice = PyTango.DeviceProxy(self.Albaemname)
            self.state = ALBAEM_STATE_MAP[str(self.AemDevice.state())]
            self.status = self.AemDevice.status()

        # TODO: Handle Exceptions properly
        except Exception as e:
            error_msg = "Could not connect with: {0}.".format(self.Albaemname)
            exception_msg = "Exception: {}".format(e)
            msg = '__init__(): {2}\n{1}'.format(error_msg, exception_msg)
            self._log.error(msg)
            # WARNING: if you raise an exception here, the pool
            # will not start if the electrometer is switch off.

    def AddDevice(self, axis):
        """Add device to controller."""
        self._log.debug("AddDevice(%d): Entering...", axis)
        self._channels.append(axis)
        # TODO: Maybe this is better to be done in DS
        # self.AemDevice.enableChannel(axis)

    def DeleteDevice(self, axis):
        """Delet device from the controller."""
        self._log.debug("DeleteDevice(%d): Entering...", axis)
        self._channels.remove(axis)

    def StateOne(self, axis):
        """Read state of one axis."""
        self._log.debug("StateOne(%d): Entering...", axis)
        return (self.state, self.status)

    def StateAll(self):
        """Read state of all axis."""
        self._log.debug("StateAll(): Entering...")
        # TODO: Add proper try/except (KeyError, AemDevice not responding)
        _state = str(self.AemDevice.state())
        self.status = self.AemDevice.status()
        self.state = ALBAEM_STATE_MAP[_state]
        # TODO: Should be return status here? ...
        return self.state

#    def PreReadOne(self, axis):
#        self._log.debug("PreReadOne(%d): Entering...", axis)
#        self.readchannels.append(axis)

    def ReadOne(self, axis):
        """Read the value of one axis."""
        # TODO: Read the channel buffer mean directly, avoid read all.
        self._log.debug("ReadOne(%d): Entering...", axis)
        if axis == 1:
            return self._integration_time

        if self._measures is not []:
            # TODO: Ensure that this is a valid value.
            return float(self._measures[axis-2])
        else:
            # NOTE: maybe ReadOne is called before measures is filled up.
            raise Exception('Last measured values not available.')

#    def PreReadAll(self):
#        self.readchannels = []
#        self._log.debug("PreReadAll(): Entering...")

    def ReadAll(self):
        """Read all the axis."""
        self._log.debug("ReadAll(): Entering...")
        if self.state == PyTango.DevState.ON:
            self._measures = self.AemDevice['Meas'].value

    def AbortOne(self, axis):
        """Stop the acquisition for one axis."""
        self._log.debug("AbortOne(%d): Entering...", axis)
#        state = self.AemDevice['state']
#        if state == PyTango.DevState.RUNNING:
#            self.AemDevice.Stop()

    def AbortAll(self):
        """Stop all the acquisitions."""
        self._log.debug("AbortAll(): Entering...")
        state = self.AemDevice.getEmState()
        if state == 'RUNNING':
            self.AemDevice.Stop()

    def PreStartAllCT(self):
        """Configure acquisition before start it."""
        self._log.debug("PreStartAllCT(): Entering...")
        self.acqchannels = []

        try:
            state = self.AemDevice.getEmState()
            # PyTango.DevState.RUNNING:
            if state == 'RUNNING':
                self.AemDevice.Stop()
            # PyTango.DevState.STANDBY:
            elif state == 'IDLE':
                self.AemDevice.StartAdc()
        except Exception as e:
            error_msg = 'Error configuring device: {}'.format(self.Albaemname)
            exception_msg = 'Exception: {}'.format(e)
            msg = 'PreStartAllCt(): {0}\n{1}'.format(error_msg, exception_msg)
            self._log.error(msg)
            # TODO: raise the proper exception.
            raise

    def PreStartOneCT(self, axis):
        """
        Record axis to be started.

        Record axis to be started so later on we can distinguish if we are
        starting only the master channel.
        """
        self._log.debug("PreStartOneCT(%d): Entering...", axis)
        self.acqchannels.append(axis)
        return True

    # def StartOneCT(self, axis):
    #     """Start acquisitionfor one axis."""
    #     self._log.debug("StartOneCT(%d): Entering...", axis)
    #     return True

    def StartAllCT(self):
        """Start acquisition for all channels in electrometer.

        Acquisition is started if only PreStartOneCT was called for the
        master channel.
        """
        self._log.debug("StartAllCT(): Entering...")
        try:
            # if self.state == PyTango.DevState.ON:
            self.AemDevice.Start()

        except Exception as e:
            error_msg = 'Could not start acquisition on: {}'.format(
                                                               self.Albaemname)
            exception_msg = 'Exception: {}'.format(e)
            msg = 'StartAllCT(): {0}\n{1}'.format(error_msg, exception_msg)
            self._log.error(msg)
            # TODO: improve exception handling.
            raise

    def PreLoadOne(self, axis, value):
        """
        Configuration needed before loading an axis.
        """
        self._log.debug("PreLoadOne(%d, %f): Entering...", axis, value)
        # TODO: This shouldn't be under an if axis == 1 ???
        if axis == 1:
            self._master = None
        # NOTE: WAIT a second ... do we really need self._master??
        # TODO: Do we need to return True? It's quite ugly.
        return True

    def LoadOne(self, axis, value):
        """
        Load one axis in controller.

        Here we are keeping a reference to the master channel, so later on,
        in StartAll(), we can distinguish if we are starting only the master
        channel.
        """
        self._log.debug("LoadOne(%d, %f): Entering...", axis, value)
        # TODO: This ... shouldn't be an if axis == 1 ?
        self._master = axis

        if self._integration_time != value:
            self._integration_time = value
        try:
            # TODO: This will be done too many times, only one is needed.
            if axis == 1:

                # TODO: This part is still not fully tested###########
                # self.sampleRate = self.AemDevice['SampleRate'].value
                # avSamples = value/self.sampleRate
                #
                # if avSamples > self.avSamplesMax:
                #     self.sampleRate = value/self.avSamplesMax
                #     self.AemDevice['SampleRate'] = self.sampleRate
                #     avSamples = value/self.sampleRate
                # #####################################################
                avSamples = value  # needed while tests are pending
                self.AemDevice['Avsamples'] = avSamples
                self.AemDevice['TriggerPeriod'] = value
                # added by zreszela 12.02.2013,
                # trigger delay is set by conitnuous scan,
                # in step scan it must be always 0
                self.AemDevice['TriggerDelay'] = 0

                # TODO: Check if this is still true
                # WARNING: The next 1 + 1 is done like this to remember that it
                #                         shoud be Points + 1 because the first
                #                         trigger arrives at 0s
                #                         at some point this will be changed in
                #                         the albaem and we will remove the + 1
                ###############################################################
                self.AemDevice['BufferSize'] = 1 + 1

            else:
                pass

        except PyTango.DevFailed as e:
            error_msg = 'Could not configure: {}'.format(self.Albaemname)
            exception_msg = 'Exception: {}'.format(e)
            msg = 'LoadOne({0}, {1}): {2}\n{3}'.format(axis, value,
                                                       error_msg,
                                                       exception_msg)
            self._log.error(msg)
            # TODO: Improve error handlig
            raise

    def GetExtraAttributePar(self, axis, name):
        """Read extra attributes."""
        # TODO: Refactor this long method.
        self._log.debug("GetExtraAttributePar(%d, %s): Entering...",
                        axis, name)
        if name.lower() == "range":
            self.ranges[axis-2] = self.AemDevice['Ranges'].value[axis-2]
            return self.ranges[axis-2]
        if name.lower() == "filter":
            self.filters[axis-2] = self.AemDevice['Filters'].value[axis-2]
            return self.filters[axis-2]
        if name.lower() == "dinversion":
            attr = 'dInversion_ch'+str(axis-1)
            self.dinversions[axis-2] = self.AemDevice[attr].value
            return self.dinversions[axis-2]
        if name.lower() == "offset":
            attr = 'offset_percentage_ch'+str(axis-1)
            self.offsets[axis-2] = self.AemDevice[attr].value
            return self.offsets[axis-2]
        if name.lower() == "samplerate":
            attr = 'SampleRate'
            self.sampleRate = self.AemDevice[attr].value
            return self.sampleRate
        if name.lower() == "autorange":
            attr = 'Autorange'
            autoRange = self.AemDevice[attr].value
            return autoRange
        # attributes used for continuous acquisition
        if name.lower() == "samplingfrequency":
            freq = 1 / self.AemDevice["samplerate"].value
            return freq
        if name.lower() == "triggermode":
            mode = self.AemDevice["TriggerMode"].value
            if mode == "INT":
                return "soft"
            if mode == "EXT":
                return "gate"
        if name.lower() == "nroftriggers":
            nrOfTriggers = self.AemDevice["BufferSize"].value
            return nrOfTriggers
        if name.lower() == "acquisitiontime":
            acqTime = self.AemDevice["AvSamples"].value
            return acqTime
        if name.lower() == "data":
            data = self.AemDevice["BufferI%d" % (axis - 1)].value
            return data

    def SetExtraAttributePar(self,axis, name, value):
        """Write extra attributes."""
        # TODO: Refactor this long method.
        if name.lower() == "range":
            self.ranges[axis-2] = value
            attr = 'range_ch' + str(axis-1)
            self.AemDevice[attr] = str(value)
        if name.lower() == "filter":
            self.filters[axis-2] = value
            attr = 'filter_ch' + str(axis-1)
            self.AemDevice[attr] = str(value)
        if name.lower() == "dinversion":
            self.dinversions[axis-2] = value
            attr = 'dInversion_ch' + str(axis-1)
            self.AemDevice[attr] = str(value)
        if name.lower() == "offset":
            self.offsets[axis-2] = value
            attr = 'offset_ch' + str(axis-1)
            self.AemDevice[attr] = str(value)
        if name.lower() == "samplerate":
            self.sampleRate = value
            attr = 'sampleRate'
            self.AemDevice[attr] = value
        if name.lower() == "autorange":
            attr = 'AutoRange'
            self.AemDevice[attr] = value
        # attributes used for continuous acquisition
        if name.lower() == "samplingfrequency":
            maxFrequency = 1000
            if value == -1 or value > maxFrequency:
                value = maxFrequency  # -1 configures maximum frequency
            rate = 1 / value
            self.AemDevice["samplerate"] = rate
        if name.lower() == "triggermode":
            if value == "soft":
                mode = "INT"
            if value == "gate":
                mode = "EXT"
            self.AemDevice["TriggerMode"] = mode
        if name.lower() == "nroftriggers":
            self.AemDevice["BufferSize"] = value
        if name.lower() == "acquisitiontime":
            self.AemDevice["TriggerDelay"] = value
            self.AemDevice["AvSamples"] = value

    def SetCtrlPar(self, par, value):
        """Set controller parameters."""
        debug_msg = 'SetCtrlPar({0}, {1}) entering...'.format(par, value)
        self._log.debug(debug_msg)
        if par == 'trigger_type':
            if value == AcqTriggerType["Software"]:
                self.AemDevice['TriggerMode'] = 'INT'
            elif value == AcqTriggerType["Gate"]:
                self.AemDevice['TriggerMode'] = 'EXT'
            else:
                exception_msg = 'Alba electrometer allows only Software or ' \
                                'Gate triggering'
                raise Exception(exception_msg)
        else:
            super(AlbaemCoTiCtrl, self).SetCtrlPar(par, value)

    def SendToCtrl(self, cmd):
        """Send a command to the controller."""
        cmd = cmd.lower()
        words = cmd.split(" ")
        ret = "Unknown command"
        # TODO: Refactor this long code.
        if len(words) == 2:
            action = words[0]
            axis = int(words[1])
            if action == "pre-start":
                msg = 'SendToCtrl({0}): pre-starting channel {1}'.format(cmd,
                                                                         axis)
                self._log.debug(msg)
                self.contAcqChannels[axis] = None
                ret = "Channel %d appended to contAcqChannels" % axis
            elif action == "start":
                msg = 'SendToCtrl({0}): starting channel {1}'.format(cmd, axis)
                self._log.debug(msg)
                self.contAcqChannels.pop(axis)
                if len(self.contAcqChannels.keys()) == 0:
                    self.AemDevice.Start()
                    ret = "Acquisition started"
                else:
                    ret = "Channel %d popped from contAcqChannels" % axis
            elif action == "pre-stop":
                msg = 'SendToCtrl({0}): pre-stopping channel {1}'.format(cmd,
                                                                         axis)
                self._log.debug(msg)
                self.contAcqChannels[axis] = None
                ret = "Channel %d appended to contAcqChannels" % axis
            elif action == "stop":
                msg = 'SendToCtrl({0}): stopping channel {1}'.format(cmd, axis)
                self._log.debug(msg)
                self.contAcqChannels.pop(axis)
                if len(self.contAcqChannels.keys()) == 0:
                    self.AemDevice.Stop()
                    ret = "Acquisition stopped"
                else:
                    ret = "Channel %d popped from contAcqChannels" % axis
        return ret

if __name__ == "__main__":
    #import time
    #obj = AlbaemCoTiCtrl('test',{'Albaemname':'ELEM01R42-020-bl29.cells.es','SampleRate':1000})
    obj = AlbaemCoTiCtrl('test',{'Albaemname':'amilan/emet/01','SampleRate':1000})
    obj.AddDevice(1)
    obj.AddDevice(2)
    obj.AddDevice(3)
    obj.AddDevice(4)
    obj.AddDevice(5)
    obj.LoadOne(1,1)
    print obj.PreStartAllCT()
    #print obj.AemDevice.setFilters([['1', 'NO'],['2', 'NO'],['3', 'NO'],['4', 'NO']])
    #print obj.AemDevice.setRanges([['1', '1mA'],['2', '1mA'],['3', '1mA'],['4', '1mA']])
    print obj.StartOneCT(1)
    print obj.StartOneCT(2)
    print obj.StartOneCT(3)
    print obj.StartOneCT(4)
    print obj.StartOneCT(5)
    print obj.StartAllCT()
    ans = obj.StateOne(1)
    ans = obj.StateOne(2)
    ans = obj.StateOne(3)
    ans = obj.StateOne(4)
    ans = obj.StateOne(5)
    ans = obj.StateAll()
    print ans
    i = 0
    while ans == PyTango.DevState.MOVING:
        print "ans:", ans
        #time.sleep(0.3)
        ans = obj.StateOne(1)
        ans = obj.StateOne(2)
        ans = obj.StateOne(3)
        ans = obj.StateOne(4)
        ans = obj.StateOne(5)
        ans = obj.StateAll()
        print obj.ReadAll()
        print obj.ReadOne(1)
        print obj.ReadOne(2)
        print obj.ReadOne(3)
        print obj.ReadOne(4)
        print obj.ReadOne(5)
        print "State is running: %s"%i
        i = i + 1
    print "ans:", ans
    print obj.ReadAll()
    print obj.ReadOne(1)
    print obj.ReadOne(2)
    print obj.ReadOne(3)
    print obj.ReadOne(4)
    print obj.ReadOne(5)
    obj.DeleteDevice(1)
    obj.DeleteDevice(2)
    obj.DeleteDevice(3)
    obj.DeleteDevice(4)
    obj.DeleteDevice(5)
