import PySpin
import numpy as np
import cv2

system = PySpin.System.GetInstance()
cam_list = system.GetCameras()
cam = cam_list.GetByIndex(0)

cam.Init()
cam.BeginAcquisition()

while True:
    image = cam.GetNextImage()
    frame = image.GetNDArray()
    
    cv2.imshow("frame", frame)
    if cv2.waitKey(1) == 27:
        break

cam.EndAcquisition()
cam.DeInit()
