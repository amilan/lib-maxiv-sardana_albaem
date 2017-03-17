#!/usr/bin/env python


"""
Test suite for the AlbaEM# sardana controller.

This test suit will test the main functionality of the AlbaEM# sardana
controller.
"""

import pytest

import PyTango
from sardana import State

from albaemcotictrl import AlbaemCoTiCtrl
from albaemcotictrl.commons import ALBAEM_STATE_MAP

__author__ = 'amilan'
__docformat__ = 'restructuredtext'


ALBAEM_DEVICE = 'ws/albaem/1'
CTRL_POSSIBLE_STATES = [State.Standby, State.On, State.Moving]


# @pytest.fixture
# def albaem(scope='session'):
#     albaemctrl = AlbaemCoTiCtrl()
#     return albaemctrl


@pytest.fixture
def albaemctrl(scope='session'):
    albaemctrl = AlbaemCoTiCtrl('test', {'Albaemname': ALBAEM_DEVICE})
    _add_devices(albaemctrl)
    return albaemctrl


@pytest.fixture
def emproxy(scope='session'):
    dp = PyTango.DeviceProxy(ALBAEM_DEVICE)
    return dp


def test_max_devices(albaemctrl):
    expected = 5
    assert hasattr(albaemctrl, 'MaxDevice')
    assert albaemctrl.MaxDevice == expected


def test_add_device(albaemctrl):
    expected = 5

    received = len(albaemctrl._channels)

    assert expected == received


def test_delete_device(albaemctrl):
    expected = 0

    _delete_devices(albaemctrl)

    received = len(albaemctrl._channels)

    assert expected == received


def test_state_one(albaemctrl):
    possible_states = CTRL_POSSIBLE_STATES

    received_states = _read_states(albaemctrl)

    assert [state in possible_states for state in received_states]


def test_state_all(albaemctrl):
    possible_states = CTRL_POSSIBLE_STATES

    received_state = _read_all_states(albaemctrl)

    assert received_state in possible_states


def test_load_one_for_axis_one(albaemctrl):
    expected = 0.5

    _load_one(albaemctrl, expected)

    received = albaemctrl._integration_time

    assert received == expected


def test_load_one_writing_acqtime(albaemctrl, emproxy):
    expected = 0.4

    _load_one(albaemctrl, expected)

    received = float(emproxy['AcqTime'].value)

    assert (expected*1000) == received


def test_pre_start_all(albaemctrl, emproxy):
    expected = State.Standby

    _pre_start_all_ct(albaemctrl)

    received = ALBAEM_STATE_MAP[emproxy['AcqState'].value.strip()]

    assert expected == received


def test_start_all(albaemctrl, emproxy):
    expected_state = State.On

    _pre_start_all_ct(albaemctrl)
    _start_all_ct(albaemctrl)

    received = ALBAEM_STATE_MAP[emproxy['AcqState'].value.strip()]

    assert received == expected_state


def test_read_one_for_axis_one(albaemctrl):
    """Test if reading from axis 1 we get the integrationTime."""
    expected = 0.5

    _load_one(albaemctrl, expected)
    received = _read_one(albaemctrl, 1)

    assert expected == received


def test_read_one_for_channels(albaemctrl):
    """Test reading each channel."""
    expected = [2, 3, 4, 5]

    albaemctrl._measures = expected
    received = [_read_one(albaemctrl, i) for i in range(2, 6)]

    assert expected == received


def test_read_all(albaemctrl):
    """Test that after reading all channels we have an array of floats."""

    _pre_start_all_ct(albaemctrl)
    _start_all_ct(albaemctrl)
    received = _read_all(albaemctrl)

    assert len(received) is 4
    assert [value is bool for value in received]


def test_abort_all(albaemctrl, emproxy):
    expected_state = State.Standby

    _abort_all(albaemctrl)

    received = ALBAEM_STATE_MAP[emproxy['AcqState'].value.strip()]

    assert expected_state == received


def _add_devices(controller):
    for i in range(1, 6):
        controller.AddDevice(i)


def _delete_devices(controller):
    for i in range(1, 6):
        controller.DeleteDevice(i)


def _read_states(controller):
    states = [controller.StateOne(i) for i in range(1, 6)]
    return states


def _read_all_states(controller):
    state = controller.StateAll()
    return state


def _load_one(controller, value):
    controller.LoadOne(1, value)


def _pre_start_all_ct(controller):
    controller.PreStartAllCT()


def _start_all_ct(controller):
    controller.StartAllCT()


def _read_one(controller, axis):
    return controller.ReadOne(axis)


def _read_all(controller):
    controller.ReadAll()
    return controller._measures


def _abort_all(controller):
    controller.AbortAll()
