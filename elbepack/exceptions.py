#
# tappyr specific exceptions
#

class TappyrError(Exception):
    tappyr_is_warning = False
    pass

class TappyrTaskSignalStatusError(TappyrError):
    pass

class TappyrTaskExitStatusError(TappyrError):
    pass

class TappyrTaskTimeoutError(TappyrError):
    pass

class TappyrMissingArgumentsError(TappyrError):
    pass

class TappyrTransportPathInvalidError(TappyrError):
    pass

class TappyrTransportPathExistsError(TappyrError):
    pass

class TappyrIOError(TappyrError):
    tappyr_is_warning = True
    pass

class TappyrDBError(TappyrError):
    tappyr_is_warning = True
    pass

class TappyrParserError(TappyrError):
    def __init__(self, node, msg, key, helptext):
        self.node = node
        self.msg = msg
        self.key = key
        self.helptext = helptext

    def __str__(self):
        msg = "Parser error\n"
        msg += "At node: %s\n" %self.node
        msg += self.msg + ": "
        msg += str(self.key)
        if self.helptext:
            msg += "\nParameter description:\n"
            msg += self.helptext
        return msg
