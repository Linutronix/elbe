# Wrapper around pexpect to avoid copies of the same wrong code

from elbepack.exceptions import *
from contextlib import contextmanager
import pexpect
import os

def child_to_msg(child):
    msg = ''
    for arg in child.args:
        msg += arg + " "
    if child.signalstatus:
        msg += ": terminated with signal status %d" %child.signalstatus
    if child.exitstatus:
        msg += ": terminated with exit status %d" %child.exitstatus
    return msg


# Ensure that a pexpect command runs in the correct path and restore
# the previous path after the command terminated by any means.
@contextmanager
def pushd(target_directory):
    prev = os.getcwd()
    if target_directory:
        os.chdir(target_directory)
    try:
        yield
    finally:
        os.chdir(prev)

# Stop a child nicely first and then brute force
# Raise a timeout exception in any case
def stop_child(child, elapsed):
    terminated = child.terminate()
    if not terminated:
       terminated = child.terminate(True)
    raise TappyrTaskTimeoutError(child, elapsed, terminated)

def __spawn(cmd, args, watchdog, timeout, logger, env, exp, **kwargs):
    # Initialize the timeout
    tick = -1
    if watchdog > 0:
        tick = watchdog
    if timeout > 0 and timeout < tick:
        tick = timeout
    elapsed = 0

    # Let it run
    child = pexpect.spawn(cmd, args, timeout = tick, env = env)
    if not child:
        return
    # Set the logger
    child.logfile = logger
    if logger:
        activity = logger.activity

    while child.isalive():
        try:
            # Use kwargs for the expect list ...
            if not exp:
                child.expect([])
            else:
                # Do something with exp
                exp_len = len(exp[0])
                i = 0
                for r,a in zip(exp[0],exp[1]):
                    if i == exp_len:
                        break
                    else:
                        child.expect(r)
                        child.sendline(a)
                    i += 1

                break
                # continue

        except pexpect.EOF:
            break
        except pexpect.TIMEOUT:
            elapsed += tick

            # If timeout, stop child and raise exception
            if timeout > 0 and elapsed >= timeout:
                stop_child(child, elapsed)

            # If logger stalled, stop child and raise exception
            if watchdog > 0 and logger:
                act = logger.activity
                if (act == activity):
                    stop_child(child, elapsed)
                actvity = act
        else:
            raise

    child.close()

    # Check the child status
    if child.signalstatus:
        raise TappyrTaskSignalStatusError(child_to_msg(child))

    if child.exitstatus != 0:
        raise TappyrTaskExitStatusError(child_to_msg(child))

def spawn(cmd, args, cwd = None, watchdog = 0, timeout = 0, logger = None,
          env = None, exp=None, **kwargs):

    with pushd(cwd):
        __spawn(cmd, args, watchdog, timeout, logger, env, exp, **kwargs)
