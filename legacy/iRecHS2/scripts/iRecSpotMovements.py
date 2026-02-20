#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import division
from __future__ import unicode_literals

# Import key parts of the PsychoPy library:
from psychopy import visual,core,event,info
import codecs
import numpy as np
import os 
from psychopy import monitors
from PIL import JpegImagePlugin
JpegImagePlugin._getmp = lambda x: None
from PIL import Image,ImageDraw,ImageFont,ImageEnhance
import SpotStimulus as SS
import irechs2 as irec

####Edit here###
M_Name='testMonitor'
M_Index=0
# Server='localhost'
Server='192.168.1.50'
####Edit here####

sp=SS.Spot(M_Name,ScreenIndex=M_Index,img=Image.open('IMG_1883.jpg'),mask='raisedCos',bg_brightness=0.5,bg_monochrome=True,bg_bokeh=16)
sp.Ready("Ready, press any key to start !")
sp.SetOrigin()



myMouse = event.Mouse(visible=False)
r=5
eye=irec.iRecHS2(Server)
if eye.state()=='connect':
    eye.start()
    while  ((eye.state()!='disconnect') & sp.WaitKeys()):
        wheel_dX, wheel_dY = myMouse.getWheelRel()
        if wheel_dY !=0:
            r+=wheel_dY*0.1
        if r > 10:
            r = 10
        if r < 1:
            r=1
        
        
        df=eye.get()
        if len(df)!=0:
            h=df['h'].mean()
            v=df['v'].mean()
            sp.SetSpot(position=(h,v),radius=r)
    eye.close()

sp.win.close()
core.quit()
