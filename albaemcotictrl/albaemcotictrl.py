#!/usr/bin/env python


"""Sardana Controller for the AlbaEM#."""

# import logging
import PyTango

# from sardana import pool
# from sardana.pool import PoolUtil
from sardana.pool.controller import CounterTimerController
# from sardana.pool import AcqTriggerType

from sardana import DataAccess
from sardana.pool.controller import NotMemorized  # MemorizedNoInit,
from sardana.pool.controller import MaxDimSize  # Memorized,

from sardana.pool.controller import Type, Description, DefaultValue, Memorize
from sardana.pool.controller import Access, FGet, FSet

from sardana import State

# from .commons import ALBAEM_STATE_MAP
# from .commons import EXTRA_ATTRIBUTES

__author__ = 'amilan'
__docformat__ = 'restructuredtext'
__all__ = ['AlbaemCoTiCtrl']


# State Map used to convert device server states into sardana states
ALBAEM_STATE_MAP = {
                    'STATE_ACQUIRING': State.Moving,
                    'STATE_ON': State.Standby,
                    'STATE_RUNNING': State.On
                    }


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
    ctrl_properties = {'Albaemname': {'Description': 'Albaem DS name',
                                      'Type': 'PyTango.DevString'},
                       }

    # NOTE: Extra attributes definition. It's done in this way because my idea
    # is split this part into another file in order to improve readability and
    # mainteinance.
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
                        # TODO: Uncomment or remove them if not needed.
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
                                # FSet: 'setNrOfTriggers'
                                },
                        # TODO: Uncomment or remove them if not needed.
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

    axis_attributes = EXTRA_ATTRIBUTES

    def __init__(self, inst, props, *args, **kwargs):
        """Class initialization."""
        # self._log.setLevel(logging.DEBUG)
        CounterTimerController.__init__(self, inst, props, *args, **kwargs)
        # self._log.setLevel(logging.INFO)
        self._log.debug("__init__(%s, %s): Entering...",
                        repr(inst), repr(props))

        self._master = None
        self._integration_time = 0.0

        # NOTE: this variable is not used at all ...
        # self.avSamplesMax = 1000

        # NOTE: Not sure that this is needed ...
        self._channels = []

        # TODO: Refactor the initialization of self._measures
        # self._measures = ['0', '0', '0', '0']
        self._measures = []

        # NOTE: the following attributes are not usefull at this moment ...
        self.lastvalues = []
        self.contAcqChannels = {}
        self.acqchannels = []
        # NOTE: If I'm not wrong this is fixed now ...
        self.sampleRate = 0.0

        self.state = None

        # TODO: Refactor the following lists
        self.ranges = ['', '', '', '']
        self.filters = ['', '', '', '']
        self.dinversions = ['', '', '', '']
        self.offsets = ['', '', '', '']

        try:
            # NOTE: ... thinking about a AlbaEMProxy class to handle the comms
            self.AemDevice = PyTango.DeviceProxy(self.Albaemname)
            self._ReadStateAndStatus()

        # TODO: Handle Exceptions properly
        except Exception as e:
            error_msg = "Could not connect with: {0}.".format(self.Albaemname)
            exception_msg = "Exception: {}".format(e)
            msg = '__init__(): {2}\n{1}'.format(error_msg, exception_msg)
            self._log.error(msg)
            # WARNING: if you raise an exception here, the pool
            # will not start if the electrometer is switch off.

    def _ReadStateAndStatus(self):
        try:
            state = (self.AemDevice['AcqState'].value).strip()
            self.state = ALBAEM_STATE_MAP[state]
            self.status = self.AemDevice.status()
            print '    Read State finished with state: {}'.format(self.state)
        # TODO: Improve the try/except please!
        except Exception as exc:
            self._log.error(exc)
            raise

    def AddDevice(self, axis):
        """Add device to controller."""
        self._log.debug("AddDevice(%d): Entering...", axis)
        self._channels.append(axis)
        print 'Channel added: {}'.format(axis)
        # NOTE: As far as I know, this is not needed now.
        # self.AemDevice.enableChannel(axis)

    def DeleteDevice(self, axis):
        """Delet device from the controller."""
        self._log.debug("DeleteDevice(%d): Entering...", axis)
        self._channels.remove(axis)

    def StateOne(self, axis):
        """Read state of one axis."""
        msg = 'StateOne({}): Entering ...'.format(axis)
        self._log.debug("StateOne(%d): Entering...", axis)
        print msg
        return (self.state, self.status)

    def StateAll(self):
        """Read state of all axis."""
        self._log.debug("StateAll(): Entering...")
        # TODO: Add proper try/except (KeyError, AemDevice not responding)
        # _state = str(self.AemDevice.state())
        try:
            self._ReadStateAndStatus()
            print 'StateAll: {}'.format(self.state)
            # TODO: Should be return status here? ...
            return self.state
        except Exception as exc:
            print 'EXCEPTIONNNN in StateAll!!!!: {}'.format(exc)

#    def PreReadOne(self, axis):
#        self._log.debug("PreReadOne(%d): Entering...", axis)
#        self.readchannels.append(axis)

    def ReadOne(self, axis):
        """Read the value of one axis."""
        msg = "ReadOne({}): Entering...".format(axis)
        self._log.debug(msg)
        print msg
        if axis == 1:
            print '  Integration time = {}'.format(self._integration_time)
            return self._integration_time

        if self._measures is not []:
            # TODO: Ensure that this is a valid value.
            meas = self._measures[axis-2]
            print '  Value for axis {0}: {1}'.format(axis, meas)
            return meas

        # NOTE: old code used for tests, to be removed.
        # attr = 'AverageCurrentCh{}'.format(axis-1)
        # # attr = 'InstantCurrentCh{}'.format(axis-1)
        # average_current = self.AemDevice[attr].value
        # print '    Instant current for attribute: {1}'.format(attr,
        #                                                       average_current
        #                                                      )
        # ndata = int(self.AemDevice['NData'].value)
        # print '        Number of triggers: {}'.format(ndata)
        # # self.AemDevice['AcqStop'] = '1'
        # return average_current

        # TODO: Pending to handle properly when self._measures is []
        # else:
        #     # NOTE: maybe ReadOne is called before measures is filled up.
        #     raise Exception('Last measured values not available.')

    def PreReadAll(self):
        self.readchannels = []
        self._log.debug("PreReadAll(): Entering...")
        print 'PreReadAll(): Entering ... '

    def ReadAll(self):
        """Read all the axis."""
        print 'ReadAll(): Entering ...'
        self._log.debug("ReadAll(): Entering...")
        # if self.state == PyTango.DevState.ON:

        self._ReadStateAndStatus()
        print '    State when ReadAll: {}'.format(self.state)
        print self.state

        if self.state is not State.Moving:
            self._SendSWTrigger()

        if self.state is State.On:

            self._measures = []
            # TODO: This should be read in only one command, but extracting
            # values from the MEAS attribute is not properly done yet.
            # NOTE: It's not ok to use the average current if the buffer hasn't
            # been cleaned after the previous scan. Is it cleared as the MEAS
            # attribute?
            for i in range(1, 5):
                # attribute_name = 'AverageCurrentCh{}'.format(i)
                attribute_name = 'CurrentCh{}'.format(i)
                values = self.AemDevice[attribute_name].value
                last_value = self._ExtractLastValue(values)
                self._measures.append(last_value)

            # # TODO: Treat this response, because the expected values are not in
            # # the same format:
            # # [['CHAN01','[]'],['CHAN02','[]'],['CHAN03', '[]'],['CHAN04','[]']]
            # _measures = self.AemDevice['Meas'].value
            # print '  Measurements: {}: '.format(_measures)
            # # TODO: maybe this shouldn't be done in the controller and it
            # # should be in the DS
            # # NOTE: Should we return the AverageCurrent instead?
            # self._measures = self._ExtractAllValues(_measures)
            # print '    Measurements after extraction: {}'.format(self._measures)

    def _SendSWTrigger(self):
        trigger_mode = self.AemDevice['TriggerMode'].value
        if trigger_mode.lower().strip() == 'software':
            print '    Sending SWTrigger!'
            self.AemDevice['SWTrigger'] = '1'

    def _ExtractLastValue(self, values):
        print 'Ready to extract values from: {}'.format(values)
        last_value = None
        try:
            last_value = float(values.strip('[]\r').split(',')[-1])
            print '    Last value = {}'.format(last_value)
            return last_value
        except Exception as e:
            print 'Error extracting last value'

    def _ExtractAllValues(self, measurements):
        """
        Extract the last value acquired.

        We know the channel by the position in the array. This could be
        improved and use a proper data structure.
        """
        print '    Extracting values for: {}'.format(measurements)
        # [['CHAN01','[1, 2, ...]'], ...]
        # list_of_values = [meas[1] for meas in measurements]
        # ['[]','[]', ...]
        # m = [meas[1].strip("[]").split(',')[-1] for meas in measurements]

        values = []
        for meas in measurements:
            print "    Meas: {}".format(meas)
            if meas[1] is not '[]':
                values.append(meas[1].strip("[]").split(',')[-1])
            else:
                print '    Values were empty!!!!'
        print '    Extracted values: {}'.format(m)
        return m

    def AbortOne(self, axis):
        """Stop the acquisition for one axis."""
        self._log.debug("AbortOne(%d): Entering...", axis)
#        state = self.AemDevice['state']
#        if state == PyTango.DevState.RUNNING:
#            self.AemDevice.Stop()

    def AbortAll(self):
        """Stop all the acquisitions."""
        self._log.debug("AbortAll(): Entering...")
        self._StopAcquisition()

    # TODO: Add decorator ensure_comms
    def _StopAcquisition(self):
        # NOTE: If we always send the AcqStop, we don't need to read the state
        # self._ReadStateAndStatus()

        # NOTE: this if is useless it will be always true
        # if self.state == 'STATE_ACQUIRING' or self.state == 'STATE_RUNNING':
        # NOTE: up to now I haven't seen any problem stopping acq like this
        # even if it's already stopped.

        self.AemDevice['AcqStop'] = '1'

    def PreStartAllCT(self):
        """Configure acquisition before start it."""
        self._log.debug("PreStartAllCT(): Entering...")
        print 'PreStartAllCT(): Entering ...'
        self.acqchannels = []

        try:
            self._StopAcquisition()
        except Exception as e:
            # TODO: Create a decorator to handle this kind of exceptions.
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
        msg = "PreStartOneCT({}): Entering...".format(axis)
        self._log.debug("PreStartOneCT(%d): Entering...", axis)
        print msg
        # NOTE: Not sure if this is worthy.
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
        print 'StartAllCT(): Entering ...'
        try:
            self._ReadStateAndStatus()
            if self.state == State.Standby:
                self.AemDevice['AcqStart'] = '1'

        except Exception as e:
            # TODO: Again ... a decorator here will make the code cleaner.
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
        msg = "PreLoadOne({0}, {1}): Entering...".format(axis, value)
        self._log.debug("PreLoadOne(%d, %f): Entering...", axis, value)
        print msg
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
        msg = "LoadOne({0}, {1}): Entering...".format(axis, value)
        self._log.debug("LoadOne(%d, %f): Entering...", axis, value)
        # TODO: This ... shouldn't be an if axis == 1 ?
        self._master = axis

        if self._integration_time != value:
            self._integration_time = value
        try:
            # TODO: Do we want this? Let's configure it by hand at the begining
            if axis == 1:
                self.AemDevice['AcqStop'] = '1'
                # TODO: Solve this bug: acqtime must be sent twice ... weird
                # UPDATE: it's even worst ... it's not working ...
                val = str(int(value * 1000))
                for i in range(2):
                    self.AemDevice['AcqTime'] = val
            #
            #     # TODO: This part is still not fully tested###########
            #     # self.sampleRate = self.AemDevice['SampleRate'].value
            #     # avSamples = value/self.sampleRate
            #     #
            #     # if avSamples > self.avSamplesMax:
            #     #     self.sampleRate = value/self.avSamplesMax
            #     #     self.AemDevice['SampleRate'] = self.sampleRate
            #     #     avSamples = value/self.sampleRate
            #     # #####################################################
            #     avSamples = value  # needed while tests are pending
            #     self.AemDevice['Avsamples'] = avSamples
            #     self.AemDevice['TriggerPeriod'] = value
            #     # added by zreszela 12.02.2013,
            #     # trigger delay is set by conitnuous scan,
            #     # in step scan it must be always 0
            #     self.AemDevice['TriggerDelay'] = 0
            #
            #     # TODO: Check if this is still true
            #     # WARNING: The next 1 + 1 is done like this to remember that it
            #     #                         shoud be Points + 1 because the first
            #     #                         trigger arrives at 0s
            #     #                         at some point this will be changed in
            #     #                         the albaem and we will remove the + 1
            #     ###############################################################
            #     self.AemDevice['BufferSize'] = 1 + 1

            # else:
            #     pass

        except PyTango.DevFailed as e:
            error_msg = 'Could not configure: {}'.format(self.Albaemname)
            exception_msg = 'Exception: {}'.format(e)
            msg = 'LoadOne({0}, {1}): {2}\n{3}'.format(axis, value,
                                                       error_msg,
                                                       exception_msg)
            self._log.error(msg)
            # TODO: Improve error handlig
            raise

    def getRange(self, axis):
        attr = 'CARangeCh{}'.format(axis)
        # NOTE: axis - 2 because it start in 1 and the 1st is the timer.
        # NOTE: Do we need the 1st to act as timer?
        # self.ranges[axis-2] = self.AemDevice['Ranges'].value[axis-2]
        self.ranges[axis-2] = self.AemDevice[attr].value
        return self.ranges[axis-2]

    def getFilter(self, axis):
        attr = 'CAFilterCh{}'.format(axis)
        self.filters[axis-2] = self.AemDevice[attr].value
        return self.filters[axis-2]

    def getInversion(self, axis):
        attr = 'CAInversionCh{}'.format(axis)
        self.dinversions[axis-2] = self.AemDevice[attr].value
        return self.dinversions[axis-2]

    # TODO: update this method when attribute available in DS
    # def getOffset(self, axis):
    #     attr = 'offset_percentage_ch'+str(axis-1)
    #     self.offsets[axis-2] = self.AemDevice[attr].value
    #     return self.offsets[axis-2]

    # def getSampleRate(self, axis):
    #     attr = 'SampleRate'
    #     # TODO: Don't repeat yoursefl and make a method with the next 2 lines.
    #     self.sampleRate = self.AemDevice[attr].value
    #     return self.sampleRate

    # def getAutoRange(self, axis):
    #     attr = 'Autorange'
    #     autoRange = self.AemDevice[attr].value
    #     return autoRange
    #
    # # attributes used for continuous acquisition
    # def getSamplingFrequency(self, axis):
    #     freq = 1 / self.AemDevice["samplerate"].value
    #     return freq

    def getTriggerMode(self, axis):
        # TODO: Refactor this!
        mode = self.AemDevice["TriggerMode"].value
        # if mode == "INT":
        #     return "soft"
        # if mode == "EXT":
        #     return "gate"

    def getNrOfTriggers(self, axis):
        nrOfTriggers = int(self.AemDevice["NData"].value)
        return nrOfTriggers

    # def getAcquisitionTime(self, axis):
    #     acqTime = self.AemDevice["AvSamples"].value
    #     return acqTime

    def getData(self, axis):
        attr = 'CurrentCh{}'.format(axis-1)
        data = self.AemDevice[attr].value
        return data

    def setRange(self, axis, value):
        self.ranges[axis-2] = value
        attr = 'CARangeCh{}' + str(axis-1)
        self.AemDevice[attr] = str(value)

    def setFilter(self, axis, value):
        self.filters[axis-2] = value
        attr = 'CAFilterCh{}' + str(axis-1)
        self.AemDevice[attr] = str(value)

    def setInversion(self, axis, value):
        self.dinversions[axis-2] = value
        attr = 'CAInversionCh{}' + str(axis-1)
        self.AemDevice[attr] = str(value)

    # TODO: update this method when attribute available in DS
    # def setOffset(self, axis, value):
    #     self.offsets[axis-2] = value
    #     attr = 'offset_ch' + str(axis-1)
    #     self.AemDevice[attr] = str(value)

    # def setSampleRate(self, axis, value):
    #     self.sampleRate = value
    #     attr = 'sampleRate'
    #     self.AemDevice[attr] = value

    # def setAutoRange(self, axis, value):
    #     attr = 'AutoRange'
    #     self.AemDevice[attr] = value

    # def setSamplingFrequency(self, axis, value):
    #     maxFrequency = 1000
    #     if value == -1 or value > maxFrequency:
    #         value = maxFrequency  # -1 configures maximum frequency
    #     rate = 1 / value
    #     self.AemDevice["samplerate"] = rate

    def setTriggerMode(self, axis, value):
        # TODO: Ensure this works like this
        if value.lower() == "software":
            mode = "SOFTWARE"
        if value.lower() == "hardware":
            mode = "HARDWARE"
        self.AemDevice["TriggerMode"] = mode

    # NOTE: Now it's read only.
    # def setNrOfTriggers(self, axis, value):
    #     self.AemDevice["BufferSize"] = value

    # def setAcquisitionTime(self, axis, value):
    #     self.AemDevice["TriggerDelay"] = value
    #     self.AemDevice["AvSamples"] = value

    # NOTE: Not sure if it's needed.
    # def SetCtrlPar(self, par, value):
    #     """Set controller parameters."""
    #     debug_msg = 'SetCtrlPar({0}, {1}) entering...'.format(par, value)
    #     self._log.debug(debug_msg)
    #     if par == 'trigger_type':
    #         if value == AcqTriggerType["Software"]:
    #             self.AemDevice['TriggerMode'] = 'INT'
    #         elif value == AcqTriggerType["Gate"]:
    #             self.AemDevice['TriggerMode'] = 'EXT'
    #         else:
    #             exception_msg = 'Alba electrometer allows only Software or ' \
    #                             'Gate triggering'
    #             raise Exception(exception_msg)
    #     else:
    #         super(AlbaemCoTiCtrl, self).SetCtrlPar(par, value)

    # NOTE: Not sure if this is needed
    # def SendToCtrl(self, cmd):
    #     """Send a command to the controller."""
    #     cmd = cmd.lower()
    #     words = cmd.split(" ")
    #     ret = "Unknown command"
    #     # TODO: Refactor this long code.
    #     if len(words) == 2:
    #         action = words[0]
    #         axis = int(words[1])
    #         if action == "pre-start":
    #             msg = 'SendToCtrl({0}): pre-starting channel {1}'.format(cmd,
    #                                                                      axis)
    #             self._log.debug(msg)
    #             self.contAcqChannels[axis] = None
    #             ret = "Channel %d appended to contAcqChannels" % axis
    #         elif action == "start":
    #             msg = 'SendToCtrl({0}): starting channel {1}'.format(cmd, axis)
    #             self._log.debug(msg)
    #             self.contAcqChannels.pop(axis)
    #             if len(self.contAcqChannels.keys()) == 0:
    #                 self.AemDevice.Start()
    #                 ret = "Acquisition started"
    #             else:
    #                 ret = "Channel %d popped from contAcqChannels" % axis
    #         elif action == "pre-stop":
    #             msg = 'SendToCtrl({0}): pre-stopping channel {1}'.format(cmd,
    #                                                                      axis)
    #             self._log.debug(msg)
    #             self.contAcqChannels[axis] = None
    #             ret = "Channel %d appended to contAcqChannels" % axis
    #         elif action == "stop":
    #             msg = 'SendToCtrl({0}): stopping channel {1}'.format(cmd, axis)
    #             self._log.debug(msg)
    #             self.contAcqChannels.pop(axis)
    #             if len(self.contAcqChannels.keys()) == 0:
    #                 self.AemDevice.Stop()
    #                 ret = "Acquisition stopped"
    #             else:
    #                 ret = "Channel %d popped from contAcqChannels" % axis
    #     return ret

if __name__ == "__main__":
    # TODO: move this code to a test unter ../tests
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
