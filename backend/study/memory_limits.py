"""Parser memory guards reused from remote commit 448d2e9.

Applied only inside disposable parser workers, never the API process.
"""
import os

PARSER_MEMORY_BYTES = 2 * 1024 * 1024 * 1024
_WINDOWS_PARSER_JOB = None


def _apply_windows_parser_memory_limit() -> None:
    """Put this parser process in a kill-on-close Windows memory-limited job."""
    global _WINDOWS_PARSER_JOB
    if _WINDOWS_PARSER_JOB is not None:
        return
    import ctypes
    from ctypes import wintypes

    class IoCounters(ctypes.Structure):
        _fields_ = [(name, ctypes.c_ulonglong) for name in (
            'ReadOperationCount', 'WriteOperationCount', 'OtherOperationCount',
            'ReadTransferCount', 'WriteTransferCount', 'OtherTransferCount')]

    class BasicLimitInformation(ctypes.Structure):
        _fields_ = [
            ('PerProcessUserTimeLimit', ctypes.c_longlong),
            ('PerJobUserTimeLimit', ctypes.c_longlong),
            ('LimitFlags', wintypes.DWORD),
            ('MinimumWorkingSetSize', ctypes.c_size_t),
            ('MaximumWorkingSetSize', ctypes.c_size_t),
            ('ActiveProcessLimit', wintypes.DWORD),
            ('Affinity', ctypes.c_size_t),
            ('PriorityClass', wintypes.DWORD),
            ('SchedulingClass', wintypes.DWORD),
        ]

    class ExtendedLimitInformation(ctypes.Structure):
        _fields_ = [
            ('BasicLimitInformation', BasicLimitInformation),
            ('IoInfo', IoCounters),
            ('ProcessMemoryLimit', ctypes.c_size_t),
            ('JobMemoryLimit', ctypes.c_size_t),
            ('PeakProcessMemoryUsed', ctypes.c_size_t),
            ('PeakJobMemoryUsed', ctypes.c_size_t),
        ]

    kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel32.CreateJobObjectW.argtypes = (ctypes.c_void_p, wintypes.LPCWSTR)
    kernel32.CreateJobObjectW.restype = wintypes.HANDLE
    kernel32.SetInformationJobObject.argtypes = (
        wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD)
    kernel32.SetInformationJobObject.restype = wintypes.BOOL
    kernel32.GetCurrentProcess.restype = wintypes.HANDLE
    kernel32.AssignProcessToJobObject.argtypes = (wintypes.HANDLE, wintypes.HANDLE)
    kernel32.AssignProcessToJobObject.restype = wintypes.BOOL
    kernel32.CloseHandle.argtypes = (wintypes.HANDLE,)
    kernel32.CloseHandle.restype = wintypes.BOOL

    job = kernel32.CreateJobObjectW(None, None)
    if not job:
        raise OSError(ctypes.get_last_error(), 'Could not create parser memory job')
    try:
        information = ExtendedLimitInformation()
        information.BasicLimitInformation.LimitFlags = 0x00000100 | 0x00002000
        information.ProcessMemoryLimit = PARSER_MEMORY_BYTES
        if not kernel32.SetInformationJobObject(job, 9, ctypes.byref(information), ctypes.sizeof(information)):
            raise OSError(ctypes.get_last_error(), 'Could not set parser memory limit')
        if not kernel32.AssignProcessToJobObject(job, kernel32.GetCurrentProcess()):
            raise OSError(ctypes.get_last_error(), 'Could not assign parser memory job')
    except BaseException:
        kernel32.CloseHandle(job)
        raise
    # Retain the only handle for the worker lifetime. Closing it at process exit
    # enforces JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE for any unexpected descendants.
    _WINDOWS_PARSER_JOB = job


def apply_parser_memory_limit() -> None:
    if os.name == 'nt':
        _apply_windows_parser_memory_limit()
        return
    try:
        import resource
        _, current_hard = resource.getrlimit(resource.RLIMIT_AS)
        ceiling = min(PARSER_MEMORY_BYTES, current_hard) if current_hard > 0 else PARSER_MEMORY_BYTES
        resource.setrlimit(resource.RLIMIT_AS, (ceiling, ceiling))
    except (ImportError, OSError, ValueError):
        # Unsupported POSIX variants retain the independent process, time and
        # output bounds. Windows failures do not reach this fallback.
        pass
