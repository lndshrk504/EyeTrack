import ctypes
for lib in ["libcudart.so.11.0", "libnvinfer.so.7", "libnvinfer_plugin.so.7"]:
    try:
        ctypes.CDLL(lib)
        print("found:", lib)
    except OSError as e:
        print("missing:", lib, "=>", e)
