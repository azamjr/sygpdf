"""Read the private parent process pipe. Run one bounded conversion and exit."""
import os
import pickle
import resource
import sys

resource.setrlimit(resource.RLIMIT_AS, (1024 ** 3, 1024 ** 3))
resource.setrlimit(resource.RLIMIT_CPU, (75, 80))
resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
result = os.fdopen(os.dup(1), 'wb')
os.dup2(2, 1)
def run(tool, files, opts):
    if tool in {"ocr", "office2pdf"}:
        from advanced import process
        import ctypes
        import errno
        # Apply a network restriction inherited by native conversion subprocesses.
        sec = ctypes.CDLL("libseccomp.so.2")
        sec.seccomp_init.restype = ctypes.c_void_p
        ctx = ctypes.c_void_p(sec.seccomp_init(0x7fff0000))
        class Comparison(ctypes.Structure):
            _fields_ = [("arg",ctypes.c_uint),("op",ctypes.c_uint),("a",ctypes.c_uint64),("b",ctypes.c_uint64)]
        for family in (2, 10):
            compare = Comparison(0, 4, family, 0)
            if sec.seccomp_rule_add_array(ctx, 0x50000 | errno.EACCES, sec.seccomp_syscall_resolve_name(b"socket"), 1, ctypes.byref(compare)):
                raise ValueError("Unable to isolate the converter.")
        if sec.seccomp_load(ctx):
            raise ValueError("Unable to isolate the converter.")
        sec.seccomp_release(ctx)
    else:
        from engine import process
    return process(tool, files, opts)

try:
    name, data = run(*pickle.load(sys.stdin.buffer))
    if len(data) > 128 * 1024 ** 2:
        raise ValueError("Result exceeds 128 MiB.")
    result.write(b"OK\n" + name.encode() + b"\n" + data)
except ValueError as exc:
    result.write(b"ERR\n" + str(exc).encode())
except Exception:
    result.write(b"ERR\nUnable to process this file. Check its format and settings.")
result.close()
