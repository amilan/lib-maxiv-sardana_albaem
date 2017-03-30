#!/usr/bin/env python


"""Sardana Controller for the AlbaEM#."""

# import logging
import time

import PyTango

# from sardana import pool
# from sardana.pool import PoolUtil
from sardana.pool.controller import CounterTimerController
# from sardana.pool import AcqTriggerType

# from sardana import DataAccess
# from sardana.pool.controller import NotMemorized  # MemorizedNoInit,
# from sardana.pool.controller import MaxDimSize  # Memorized,
#
# from sardana.pool.controller import Type, Description, DefaultValue, Memorize
# from sardana.pool.controller import Access, FGet, FSet

from sardana import State

from commons import ALBAEM_STATE_MAP
from attributes import EXTRA_ATTRIBUTES
from decorators import alert_problems

__author__ = 'amilan'
__docformat__ = 'restructuredtext'
__all__ = ['AlbaemCoTiCtrl']


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

        self._ConnectToAlbaEM()
        self._ReadStateAndStatus()

    @alert_problems
    def _ConnectToAlbaEM(self):
        # NOTE: ... thinking about a AlbaEMProxy class to handle the comms
        self.AemDevice = PyTango.DeviceProxy(self.Albaemname)

    @alert_problems
    def _ReadStateAndStatus(self):
        state = (self.AemDevice['AcqState'].value).strip()
        self.state = ALBAEM_STATE_MAP[state]
        self.status = self.AemDevice.status()
        print '    Read State finished with state: {0}'.format(self.state)
        # NOTE: maybe we should handle also the state to Fault!!

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
        self._ReadStateAndStatus()
        print 'StateAll: {0}'.format(self.state)
        # TODO: Should be return status here? ...
        return self.state

#    def PreReadOne(self, axis):
#        self._log.debug("PreReadOne(%d): Entering...", axis)
#        self.readchannels.append(axis)

    def ReadOne(self, axis):
        """Read the value of one axis."""
        msg = "ReadOne({0}): Entering...".format(axis)
        self._log.debug(msg)
        print msg
        if axis == 1:
            print '  Integration time = {0}'.format(self._integration_time)
            return self._integration_time

        # MMM.... THIS WILL ALWAYS BE TRUE!!!
        #if self._measures is not []:
        if len(self._measures) > 0:
            # TODO: Ensure that this is a valid value.
            meas = self._measures[axis-2]
            print '  Value for axis {0}: {1}'.format(axis, meas)
            return meas

        # NOTE: old code used for tests, to be removed.
        # attr = 'AverageCurrentCh{0}'.format(axis-1)
        # # attr = 'InstantCurrentCh{0}'.format(axis-1)
        # average_current = self.AemDevice[attr].value
        # print '    Instant current for attribute: {1}'.format(attr,
        #                                                       average_current
        #                                                      )
        # ndata = int(self.AemDevice['NData'].value)
        # print '        Number of triggers: {0}'.format(ndata)
        # # self.AemDevice['AcqStop'] = '1'
        # return average_current

        # TODO: Pending to handle properly when self._measures is []
        # else:
        #     # NOTE: maybe ReadOne is called before measures is filled up.
        #     raise Exception('Last measured values not available.')

    # NOTE: Not in use ...
    # def PreReadAll(self):
    #     self.readchannels = []
    #     self._log.debug("PreReadAll(): Entering...")
    #     print 'PreReadAll(): Entering ... '

    def ReadAll(self):
        """Read all the axis."""
        print 'ReadAll(): Entering ...'
        self._log.debug("ReadAll(): Entering...")
        # if self.state == PyTango.DevState.ON:

        #if self.state is not State.Moving:
        #    self._SendSWTrigger()

        # TODO: This should be read in only one command, but extracting
        # values from the MEAS attribute is not properly done yet.
        # NOTE: It's not ok to use the average current if the buffer hasn't
        # been cleaned after the previous scan. Is it cleared as the MEAS
        # attribute?
        self._measures = []
        for i in range(1, 5):
            # attribute_name = 'AverageCurrentCh{}'.format(i)
            attribute_name = 'CurrentCh{0}'.format(i)
            last_value = self._ExtractLastValue(attribute_name)
            self._measures.append(last_value)

        # # TODO: Treat this response, because the expected values are not in
        # # the same format:
        # # [['CHAN01','[]'],['CHAN02','[]'],['CHAN03', '[]'],['CHAN04','[]']]
        # _measures = self.AemDevice['Meas'].value
        # print '  Measurements: {0}: '.format(_measures)
        # # TODO: maybe this shouldn't be done in the controller and it
        # # should be in the DS
        # # NOTE: Should we return the AverageCurrent instead?
        # self._measures = self._ExtractAllValues(_measures)
        # print '    Measurements after extraction: {0}'.format(self._measures)

    @alert_problems
    def _SendSWTrigger(self):
        trigger_mode = self.AemDevice['TriggerMode'].value
        if trigger_mode.lower().strip() == 'software':
            print '    Sending SWTrigger!'
            self.AemDevice['SWTrigger'] = '1'

    @alert_problems
    def _ExtractLastValue(self, attribute_name):
        values = self.AemDevice[attribute_name].value
        last_value = values.strip('[]\r').split(',')[-1]
        if last_value == '':
            last_value = 'nan'
        return float(last_value)

    # TODO: To be used once is used by ReadAll
    # def _ExtractAllValues(self, measurements):
    #     """
    #     Extract the last value acquired.
    #
    #     We know the channel by the position in the array. This could be
    #     improved and use a proper data structure.
    #     """
    #     print '    Extracting values for: {0}'.format(measurements)
    #     # [['CHAN01','[1, 2, ...]'], ...]
    #     # list_of_values = [meas[1] for meas in measurements]
    #     # ['[]','[]', ...]
    #     # m = [meas[1].strip("[]").split(',')[-1] for meas in measurements]
    #
    #     values = []
    #     for meas in measurements:
    #         print "    Meas: {0}".format(meas)
    #         if meas[1] is not '[]':
    #             values.append(meas[1].strip("[]").split(',')[-1])
    #         else:
    #             print '    Values were empty!!!!'
    #     print '    Extracted values: {0}'.format(m)
    #     return m

    # NOTE: We don't really need reimplement this method now.
#     def AbortOne(self, axis):
#         """Stop the acquisition for one axis."""
#         self._log.debug("AbortOne(%d): Entering...", axis)
# #        state = self.AemDevice['state']
# #        if state == PyTango.DevState.RUNNING:
# #            self.AemDevice.Stop()

    @alert_problems
    def AbortAll(self):
        """Stop all the acquisitions."""
        self._log.debug("AbortAll(): Entering...")
        self._StopAcquisition()
    
    @alert_problems
    def AbortOne(self, axis):
        """Stop all the acquisitions."""
        self._log.debug("AbortOne(%r): Entering..."%axis)
        self._StopAcquisition()
  
    @alert_problems
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

        # NOTE: If we only write the AcqStop attribute the method is useless
        self._StopAcquisition()

    def PreStartOneCT(self, axis):
        return True
    # NOTE: Not really useful right now.
    # def PreStartOneCT(self, axis):
    #     """
    #     Record axis to be started.
    #
    #     Record axis to be started so later on we can distinguish if we are
    #     starting only the master channel.
    #     """
    #     msg = "PreStartOneCT({0}): Entering...".format(axis)
    #     self._log.debug("PreStartOneCT(%d): Entering...", axis)
    #     print msg
    #     # NOTE: Not sure if this is worthy.
    #     self.acqchannels.append(axis)
    #     return True

    # def StartOneCT(self, axis):
    #     """Start acquisitionfor one axis."""
    #     self._log.debug("StartOneCT(%d): Entering...", axis)
    #     return True

    @alert_problems
    def StartAllCT(self):
        """Start acquisition for all channels in electrometer.

        Acquisition is started if only PreStartOneCT was called for the
        master channel.
        """
        self._log.debug("StartAllCT(): Entering...")
        print 'StartAllCT(): Entering ...'
        self.AemDevice['AcqStop'] = '1'
        time.sleep(.1)
        while self.state != State.On:
            self._ReadStateAndStatus()
        self.AemDevice['TriggerMode'] = '0'
        time.sleep(.1)
        # TODO: ensure this attribute is present in the DS
        # self.AemDevice['NTrig'] = '1'
        time.sleep(.1)
        self.AemDevice['AcqStart'] = '1'
        time.sleep(.1)
        while self.state != State.Moving:
            self._ReadStateAndStatus()
        # We have to be sure that there is a State Transition
        # if not, it may be possible that we return previous values
        self.AemDevice['SWTrigger'] = '1'
        #time.sleep(.1)

    # TODO: Ensure that this method is needed.
    # def PreLoadOne(self, axis, value):
    #     """Configuration needed before loading an axis."""
    #     msg = "PreLoadOne({0}, {1}): Entering...".format(axis, value)
    #     self._log.debug("PreLoadOne(%d, %f): Entering...", axis, value)
    #     print msg
    #     # TODO: This shouldn't be under an if axis == 1 ???
    #     if axis == 1:
    #         self._master = None
    #     # NOTE: WAIT a second ... do we really need self._master??
    #     # TODO: Do we need to return True? It's quite ugly.
    #     return True

    @alert_problems
    def LoadOne(self, axis, value):
        """
        Load one axis in controller.

        Here we are keeping a reference to the master channel, so later on,
        in StartAll(), we can distinguish if we are starting only the master
        channel.
        """
        msg = "LoadOne({0}, {1}): Entering...".format(axis, value)
        self._log.debug(msg)
        print msg
        # TODO: This ... shouldn't be an if axis == 1 ?
        self._master = axis

        self._integration_time = value

        if axis == 1:
            self.AemDevice['AcqStop'] = '1'
            # NOTE: if we don't wait a little bit, the acqtime is not
            # configured properly.
            time.sleep(0.5)
            val = str(int(value * 1000))
            self.AemDevice['AcqTime'] = val

    # NOTE: Kind of ugly to have the definition and implementation in different
    #       files ... think about how to better connect them. The main problem
    #       at this time, it's the AemDevice instance, which is created in the
    #       controller ...
    @alert_problems
    def getRange(self, axis):
        attr = 'CARangeCh{0}'.format(axis)
        # NOTE: axis - 2 because it start in 1 and the 1st is the timer.
        # NOTE: Do we need the 1st to act as timer?
        # self.ranges[axis-2] = self.AemDevice['Ranges'].value[axis-2]
        self.ranges[axis-2] = self.AemDevice[attr].value
        return self.ranges[axis-2]

    @alert_problems
    def getFilter(self, axis):
        attr = 'CAFilterCh{0}'.format(axis)
        self.filters[axis-2] = self.AemDevice[attr].value
        return self.filters[axis-2]

    @alert_problems
    def getInversion(self, axis):
        attr = 'CAInversionCh{0}'.format(axis)
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

    @alert_problems
    def getTriggerMode(self, axis):
        # TODO: Refactor this!
        mode = self.AemDevice["TriggerMode"].value
        # if mode == "INT":
        #     return "soft"
        # if mode == "EXT":
        #     return "gate"

    @alert_problems
    def getNrOfTriggers(self, axis):
        nrOfTriggers = int(self.AemDevice["NData"].value)
        return nrOfTriggers

    # def getAcquisitionTime(self, axis):
    #     acqTime = self.AemDevice["AvSamples"].value
    #     return acqTime

    @alert_problems
    def getData(self, axis):
        attr = 'CurrentCh{0}'.format(axis-1)
        data = self.AemDevice[attr].value
        return data

    @alert_problems
    def setRange(self, axis, value):
        self.ranges[axis-2] = value
        attr = 'CARangeCh{0}' + str(axis-1)
        self.AemDevice[attr] = str(value)

    @alert_problems
    def setFilter(self, axis, value):
        self.filters[axis-2] = value
        attr = 'CAFilterCh{0}' + str(axis-1)
        self.AemDevice[attr] = str(value)

    @alert_problems
    def setInversion(self, axis, value):
        self.dinversions[axis-2] = value
        attr = 'CAInversionCh{0}' + str(axis-1)
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

    @alert_problems
    def setTriggerMode(self, axis, value):
        # TODO: Ensure this works like this
        if value.lower() == "software":
            mode = "SOFTWARE"
            # STRING FOR MODE DOES NOT WORK...
            mode = 0
        if value.lower() == "hardware":
            mode = "HARDWARE"
            # STRING FOR MODE DOES NOT WORK...
            mode = 1
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
