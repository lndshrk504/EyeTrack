import deeplabcut, dlclive, tensorflow as tf
print("DLC:", getattr(deeplabcut, "__version__", "n/a"))
print("dlclive:", getattr(dlclive, "__version__", "n/a"))
print("TF:", tf.__version__)
