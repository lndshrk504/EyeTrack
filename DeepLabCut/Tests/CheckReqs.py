import os
import tensorflow as tf
from tensorflow.python.platform import build_info

print("TF:", tf.__version__)
print("Build CUDA:", build_info.build_info.get("cuda_version"))
print("Build cuDNN:", build_info.build_info.get("cudnn_version"))
print("Build TRT:", build_info.build_info.get("tensorrt_version"))
print("LD_LIBRARY_PATH:", os.environ.get("LD_LIBRARY_PATH", ""))
