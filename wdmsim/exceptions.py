

class WavelengthLockException(Exception):
    pass

class DuplicateLockException(WavelengthLockException):
    pass

class ZeroLockException(WavelengthLockException):
    pass

