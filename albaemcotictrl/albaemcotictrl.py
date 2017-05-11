#!/usr/bin/env python


"""Sardana Controller for the AlbaEM#."""

import time
import re

import PyTango
import taurus

from sardana.pool.controller import CounterTimerController

from sardana import State

from commons import ALBAEM_STATE_MAP, DEFAULT_SLEEP_TIME
from attributes import EXTRA_ATTRIBUTES
from decorators import alert_problems, timing_me

__author__ = 'amilan'
__docformat__ = 'restructuredtext'
__all__ = ('AlbaemCoTiCtrl')


class AlbaemCoTiCtrl(CounterTimerController):
    """
    Sardana CounterTimer controller for the Alba Electrometer.

    This controller is used to manage the controll of an Alba EM#.
    You will need to define 5 elements for this controller, being the first one
    the time to be used and the following 4 the channels of the EM#.

    In order to configure it, you only need to define the property: Albaemname,
    passing the value of a valid Skippy Tango Device Server already configured
    to work with an EM#.
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

        self._log.debug("__init__(%s, %s): Entering...",
                        repr(inst), repr(props))

        self._master = None
        self._integration_time = 0.0

        # NOTE: Not sure that this is needed ...
        self._channels = []
        self._measures = []
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
        self._StopAcquisition()
        self._ConfigureDefaultTrigger()

        # regular expression to extract all values in an acquisition of only
        # 1 trigger.
        # TODO: refactor this reg. exp. to work with any number of triggers.
        self._all_values = re.compile(r"-*\d+.\d+")

    @alert_problems
    @timing_me
    def _ConnectToAlbaEM(self):
        """Method to initialize the communication channel with the EM."""
        # NOTE: ... thinking about a AlbaEMProxy class to handle the comms
        self.AemDevice = PyTango.DeviceProxy(self.Albaemname)
        # self.AemDevice = taurus.Device(self.Albaemname)

    @alert_problems
    @timing_me
    def _ReadStateAndStatus(self):
        """Method to update the state and status values."""
        # state = (self.AemDevice['AcqState'].value).strip()
        state = self._get_aem_state()

        self.state = ALBAEM_STATE_MAP[state]

        # self.status = self.AemDevice.status()
        self._get_aem_status()

        # print '    Read State finished with state: {0}'.format(self.state)
        # NOTE: maybe we should handle also the state to Fault!!

        # NOTE: this return is used to debug the controller.
        return self.state


    # NOTE: temporal methods to test the execution time.
    @alert_problems
    @timing_me
    def _get_aem_state(self):
        # state = (self.AemDevice['AcqState'].value).strip()
        # state = (self.AemDevice.read_attribute('AcqState').value).strip()
        state = self._just_read_the_value_please()
        return state.strip()

    @timing_me
    def _just_read_the_value_please(self):
        # import pdb
        # pdb.set_trace()
        state = self.AemDevice.read_attribute('AcqState').value
        return state

    @alert_problems
    @timing_me
    def _get_aem_status(self):
        self.status = self.AemDevice.status()

    @alert_problems
    @timing_me
    def _ConfigureDefaultTrigger(self):
        """This method configures the trigger to be used by the EM."""
        # self.AemDevice['NTrig'] = '1'
        self.AemDevice.write_attribute('Ntrig', '1')
        time.sleep(DEFAULT_SLEEP_TIME)
        # self.AemDevice['TriggerMode'] = '0'
        self.AemDevice.write_attribute('TriggerMode', '0')
        time.sleep(DEFAULT_SLEEP_TIME)

    @timing_me
    def AddDevice(self, axis):
        """Add device to controller."""
        self._log.debug("AddDevice(%d): Entering...", axis)
        self._channels.append(axis)
        # print 'Channel added: {}'.format(axis)
        # NOTE: As far as I know, this is not needed now.
        # self.AemDevice.enableChannel(axis)

    @timing_me
    def DeleteDevice(self, axis):
        """Delet device from the controller."""
        self._log.debug("DeleteDevice(%d): Entering...", axis)
        self._channels.remove(axis)

    @timing_me
    def StateOne(self, axis):
        """Read state of one axis."""
        msg = 'StateOne({}): Entering ...'.format(axis)
        self._log.debug("StateOne(%d): Entering...", axis)
        # print msg
        return (self.state, self.status)

    @timing_me
    def StateAll(self):
        """Read state of all axis."""
        self._log.debug("StateAll(): Entering...")
        self._ReadStateAndStatus()
        # print 'StateAll: {0}'.format(self.state)
        # TODO: Should be return status here? ...
        return self.state

    @timing_me
    def ReadOne(self, axis):
        """
        Read the value of one axis.

        :param axis: Channel number to be read.
        :return: The channel value.
        """
        msg = "ReadOne({0}): Entering...".format(axis)
        self._log.debug(msg)
        # print msg
        if axis == 1:
            # print '  Integration time = {0}'.format(self._integration_time)
            return self._integration_time

        if len(self._measures) > 0:
            # TODO: Ensure that this is a valid value.
            meas = self._measures[axis-2]
            # print '  Value for axis {0}: {1}'.format(axis, meas)
            return meas

    @timing_me
    def ReadAll(self):
        """Read all the axis."""
        # print 'ReadAll(): Entering ...'
        self._log.debug("ReadAll(): Entering...")

        # self._measures = []
        if self.state != State.Moving:
            self._measures = self._extractAllValues()
            # for i in range(1, 5):
            #     attribute_name = 'CurrentCh{0}'.format(i)
            #     last_value = self._ExtractLastValue(attribute_name)
            #     self._measures.append(last_value)

    @alert_problems
    @timing_me
    def _extractAllValues(self):
        values = self.AemDevice['Meas'].value
        measures = [float(value) for value in self._all_values.findall(values)]
        return measures

    @alert_problems
    @timing_me
    def _SendSWTrigger(self):
        """
        Method used to send a software trigger.

        If the EM is configured in order to use software triggers, this method
        will send one.
        """
        trigger_mode = self.AemDevice['TriggerMode'].value
        if trigger_mode.lower().strip() == 'software':
            # print '    Sending SWTrigger!'
            # self.AemDevice['SWTrigger'] = '1'
            self.AemDevice.write_attribute('SWTrigger', '1')

    @alert_problems
    @timing_me
    def _sendTrigger(self):
        """The main purpose of this method is to test the comms."""
        # self.AemDevice['SWTrigger'] = '1'
        self.AemDevice.write_attribute('SWTrigger', '1')

    @alert_problems
    @timing_me
    def _ExtractLastValue(self, attribute_name):
        """
        Method to read an attribute value and extract the relevant data.

        :param attribute_name: String with the name of the attribute to be read.
        :return: Float with the actual value read.
        """
        values = self.AemDevice[attribute_name].value
        last_value = values.strip('[]\r').split(',')[-1]
        if last_value == '':
            last_value = 'nan'
        return float(last_value)

    @alert_problems
    @timing_me
    def AbortAll(self):
        """Stop all the acquisitions."""
        self._log.debug("AbortAll(): Entering...")
        self._StopAcquisition()

    @alert_problems
    @timing_me
    def AbortOne(self, axis):
        """
        Stop all the acquisitions.

        :param axis: Number corresponding to the axis to be stopped.
        """
        self._log.debug("AbortOne(%r): Entering..."%axis)
        self._StopAcquisition()

    @alert_problems
    @timing_me
    def _StopAcquisition(self):
        """Stop data acquisition in the EM."""
        # self.AemDevice['AcqStop'] = '1'
        self.AemDevice.write_attribute('AcqStop', '1')
        self._log.debug(' ... Acquisition stopped')

    @timing_me
    def PreStartAllCT(self):
        """Configure acquisition before start it."""
        self._log.debug("PreStartAllCT(): Entering...")
        # print 'PreStartAllCT(): Entering ...'
        self.acqchannels = []

        self._StopAcquisition()

    @timing_me
    def PreStartOneCT(self, axis):
        """To be executed before an axis acquisition."""
        return True

    @alert_problems
    @timing_me
    def StartAllCT(self):
        """Start acquisition for all channels in the electrometer.

        Acquisition is started if only PreStartOneCT was called for the
        master channel.
        """
        self._log.debug("StartAllCT(): Entering...")
        # print 'StartAllCT(): Entering ...'

        # # TODO: This should be out, and managed in StateAll
        # while self.state != State.On:
        #     # print '    ... State is not ON'
        #     self._ReadStateAndStatus()

        # self.AemDevice['AcqStart'] = '1'
        self._startAcquisition()
        # time.sleep(0.3)

        print '    State before while: {0}'.format(self.state)
        while self.state != State.Moving:
            # print '    ... State is not Moving'
            self._ReadStateAndStatus()
        print '    State after while: {0}'.format(self.state)
        # NOTE: We have to be sure that there is a State Transition
        #       if not, it may be possible that we return previous values
        #self.AemDevice['SWTrigger'] = '1'
        self._sendTrigger()

    @alert_problems
    @timing_me
    def _startAcquisition(self):
        # self.AemDevice['AcqStart'] = '1'
        self.AemDevice.write_attribute('AcqStart', '1')


    @alert_problems
    @timing_me
    def LoadOne(self, axis, value):
        """
        Load one axis in controller.

        Here we are keeping a reference to the master channel, so later on,
        in StartAll(), we can distinguish if we are starting only the master
        channel.

        It also configures the EM acquisition time.

        :param axis: Channel number to be configured.
        :param value: value to be set as acquisition time in the EM.
        """
        msg = "LoadOne({0}, {1}): Entering...".format(axis, value)
        self._log.debug(msg)
        # print msg
        # TODO: This ... shouldn't be an if axis == 1 ?
        self._master = axis

        self._integration_time = value

        if axis == 1:
            # self.AemDevice['AcqStop'] = '1'
            self.AemDevice.write_attribute('AcqStop', '1')
            # NOTE: if we don't wait a little bit, the acqtime is not
            # configured properly.
            time.sleep(DEFAULT_SLEEP_TIME)
            val = str(int(value * 1000))
            # self.AemDevice['AcqTime'] = val
            self.AemDevice.write_attribute('AcqTime', val)

    # NOTE: Kind of ugly to have the definition and implementation in different
    #       files ... think about how to better connect them. The main problem
    #       at this time, it's the AemDevice instance, which is created in the
    #       controller ...
    @alert_problems
    def getRange(self, axis):
        """
        Get the range of a channel in the EM.

        :param axis: Channel number to be read.
        :return: Channel's range.
        """
        attr = 'CARangeCh{0}'.format(axis)
        # NOTE: axis - 2 because it start in 1 and the 1st is the timer.
        # NOTE: Do we need the 1st to act as timer?
        # self.ranges[axis-2] = self.AemDevice['Ranges'].value[axis-2]
        self.ranges[axis-2] = self.AemDevice[attr].value
        return self.ranges[axis-2]

    @alert_problems
    def getFilter(self, axis):
        """
        Get the Filter of a channel in the EM.

        :param axis: Channel number to be read.
        :return: Channel's filter.
        """
        attr = 'CAFilterCh{0}'.format(axis)
        self.filters[axis-2] = self.AemDevice[attr].value
        return self.filters[axis-2]

    @alert_problems
    def getInversion(self, axis):
        """
        Get the inversion of a channel in the EM.

        :param axis: Channel number to be read.
        :return: Channel's inversion.
        """
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
        """
        Get the Trigger mode of the EM.

        It's not possible to set a different triger mode per channel, so here
        we are returning the value for the whole EM.

        :param axis: Channel number to be read.
        :return: EM's trigger mode.
        """
        # TODO: Refactor this!
        mode = self.AemDevice["TriggerMode"].value
        # if mode == "INT":
        #     return "soft"
        # if mode == "EXT":
        #     return "gate"

    @alert_problems
    def getNrOfTriggers(self, axis):
        """
        Get the Number of triggers for the whole EM.

        The electrometer will be acquiring until it gets these amount of
        triggers.

        :param axis: Channel number to be read.
        :return: Number of triggers to acquire.
        """
        nrOfTriggers = int(self.AemDevice['NTrig'].value)
        return nrOfTriggers

    # def getAcquisitionTime(self, axis):
    #     acqTime = self.AemDevice["AvSamples"].value
    #     return acqTime

    @alert_problems
    def getData(self, axis):
        """
        Get the current data for a channel in the EM.

        :param axis: Channel number to be read.
        :return: Channel's current.
        """
        attr = 'CurrentCh{0}'.format(axis-1)
        data = self.AemDevice[attr].value
        return data

    @alert_problems
    def setRange(self, axis, value):
        """
        Set the range of a channel in the EM.

        :param axis: Channel number to be set.
        :param value: Range value to be set.
        """
        self.ranges[axis-2] = value
        attr = 'CARangeCh{0}' + str(axis-1)
        # self.AemDevice[attr] = str(value)
        self.AemDevice.write_attribute(attr, str(value))

    @alert_problems
    def setFilter(self, axis, value):
        """
        Set the filter associated to a channel in the EM.

        :param axis: Channel number to be set.
        :param value: Filter value to be set.
        """
        self.filters[axis-2] = value
        attr = 'CAFilterCh{0}' + str(axis-1)
        # self.AemDevice[attr] = str(value)
        self.AemDevice.write_attribute(attr, str(value))

    @alert_problems
    def setInversion(self, axis, value):
        """
        Set the inversion of a channel in the EM.

        :param axis: Channel number to be set.
        :param value: Inversion value to be set.
        """
        self.dinversions[axis-2] = value
        attr = 'CAInversionCh{0}' + str(axis-1)
        # self.AemDevice[attr] = str(value)
        self.AemDevice.write_attribute(attr, str(value))

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
        """
        Set the trigger mode for the whole EM.

        :param axis: Channel number to be set.
        :param value: Range value to be set.
        """
        # TODO: This can be refactored and use a map
        if value.lower() == "software":
            mode = '0'
        if value.lower() == "hardware":
            mode = '1'
        # self.AemDevice["TriggerMode"] = mode
        self.AemDevice.write_attribute('TriggerMode', mode)

    def setNrOfTriggers(self, axis, value):
        """
        Set the number of triggers to expect in an acquisition.

        :param axis: Channel number to be set. (Doesn't really matter.)
        :param value: Number of triggers to be set.
        """
        # self.AemDevice["NTrig"] = str(value)
        self.AemDevice.write_attribute('NTrig', str(value))

    # def setAcquisitionTime(self, axis, value):
    #     self.AemDevice["TriggerDelay"] = value
    #     self.AemDevice["AvSamples"] = value
