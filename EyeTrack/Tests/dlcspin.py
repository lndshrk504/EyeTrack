from dlclive import DLCLive, Processor
import PySpin

dlc_proc = Processor()
# load exported DLC model
dlc = DLCLive("/home/wbs/DLC/DLC_PupilTracking_YangLab_resnet_50_iteration-0_shuffle-1",
        processor=dlc_proc, display=True)

# initialize camera
system = PySpin.System.GetInstance()
cam = system.GetCameras()[0]
cam.Init()
cam.BeginAcquisition()

# get first frame
img = cam.GetNextImage().GetNDArray()

dlc.init_inference(img)

while True:
    img = cam.GetNextImage().GetNDArray()
    
    pose = dlc.get_pose(img)

    print(pose)
