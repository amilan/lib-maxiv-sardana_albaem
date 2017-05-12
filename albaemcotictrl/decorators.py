#!/usr/bin/env python

"""Decorators definition for AlbaEM# sardana controller."""

from functools import wraps
import traceback
import PyTango
import sys
import time


def alert_problems(meth):
    """
    Alert comms decorator.

    Decorator to alert when there is a communication problem with the AlbaEM.
    """
    @wraps(meth)
    def _alert_problems(self, *args, **kwargs):
        try:
            return meth(self, *args, **kwargs)

        except PyTango.DevFailed:
            header = 'PyTango.DevFailed in: {}\n'.format(meth.__name__)
            print '{0:-^79}'.format(header)

            exctype, value = sys.exc_info()[:2]
            for error in value:
                print 'Reason:\t{0}\nDescription:\t{1}\nOrigin:\t{2}\n'.format(
                       error.reason, error.desc, error.origin)
            print '{0:-^79}'.format('')

        except PyTango.ConnectionFailed as e:
            error_msg = "Could not connect with the electrometer."
            exception_msg = "Exception: {}".format(e)
            msg = '__init__(): {2}\n{1}'.format(error_msg, exception_msg)
            # self._log.error(msg)
            print '{0:-^79}'.format('Connection Failed')
            print '{0}'.format(msg)
            print '{0:-^79}'.format('')

        except Exception:
            header = 'Unnexpected Error in: {0}'.format(meth.__name__)
            print '{0:-^79}'.format(header)
            traceback.print_exc()
            print '{0:-^79}'.format('')

    return _alert_problems

DEFAULT_FMT = '[{elapsed: 0.8f}s] {name}({args}) -> {result}'

def time_it(meth, fmt=DEFAULT_FMT):
    @wraps(meth)
    def timed(self, *args, **kwargs):
        t0 = time.time()
        _result = meth(self, *args, **kwargs)
        elapsed = time.time() - t0
        name = meth.__name__
        args = ', '.join(repr(args) for arg in args)
        result = repr(_result)
        print fmt.format(**locals())
        return _result
    return timed
