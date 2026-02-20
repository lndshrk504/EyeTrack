#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import division
from __future__ import unicode_literals

# Import key parts of the PsychoPy library:
from psychopy import visual,core,event,info,monitors
import codecs
import numpy as np
import os 

from PIL import JpegImagePlugin
JpegImagePlugin._getmp = lambda x: None
from PIL import Image,ImageDraw,ImageFont,ImageEnhance



class Spot():
    def __init__(self,MonitorName,ScreenIndex=0,img=None,mask='raisedCos',bg_brightness=0.5,bg_monochrome=True,bg_bokeh=8):

        self.mon=monitors.Monitor(MonitorName)
        self.win= visual.Window(fullscr=True,monitor=MonitorName,size=self.mon.getSizePix(),screen=ScreenIndex,units='pix',color='black')

        self.d_cm=self.mon.getDistance()
        self.h_pix,self.v_pix=self.mon.getSizePix()
        self.h_cm=self.mon.getWidth()
        self.offset=np.array([0,0])
        
        self.win.setMouseVisible(False)
        
        self.monsize=np.array(self.mon.getSizePix(),dtype='int')
        self.origin=(self.monsize/2).astype('int')
        if img==None:
            img=Image.new("RGB",(800,600),(255,0,0))
            
        self.fg=img
        
        if (bg_brightness< 1.0) & (bg_brightness > 0.0):
            self.bg=ImageEnhance.Brightness(img).enhance(bg_brightness)
        else:
            self.bg=img
            
        if (bg_monochrome==True):
            self.bg=self.bg.convert('L')
        
        r=min(self.fg.size/self.monsize)
        wh=(self.fg.size/r).astype('int')
        self.fg=self.fg.resize(wh,Image.LANCZOS)
        self.bg=self.bg.resize(wh,Image.LANCZOS)
        
        sx,sy=((wh-self.monsize)/2).astype('int')
        ex,ey=((sx,sy)+self.monsize)
        box=(sx,sy,ex,ey)
        self.fg=self.fg.crop(box)
        self.bg=self.bg.crop(box)
        
        if bg_bokeh>1:
            wh=np.array(self.fg.size)
            wh=(wh/bg_bokeh).astype('int')
            self.bg=self.bg.resize(wh,Image.LANCZOS)
            self.bg=self.bg.resize(self.fg.size,Image.LANCZOS)
        
        self.fimg=visual.ImageStim(self.win,image=self.fg,units='pix',interpolate=True,mask=mask)
        self.bimg=visual.ImageStim(self.win,image=self.bg,units='pix',interpolate=True)
        
        self.hline=visual.Line(self.win,units='pix',lineColor=[-1,-1,1])
        self.hline.start=[-self.h_pix/2,0]
        self.hline.end=[+self.h_pix/2,+0]
        
        self.vline=visual.Line(self.win,units='pix',lineColor=[-1,-1,1])
        self.vline.start=[0,-self.v_pix/2]
        self.vline.end=[0,+self.v_pix/2]
        
        R10w=self.deg2pix_size(20)
        R10h=self.deg2pix_size(20)
        self.R10=visual.Rect(self.win,units='pix',width=R10w,height=R10h,fillColor=None,lineColor=[-1,-1,1])
        
        
    def Ready(self,msg):
        StartText = visual.TextStim(self.win, text=msg, pos=(0, 0),wrapWidth=1000,height=30,units='pix')
        StartText.draw()
        self.win.flip()
        event.waitKeys()
        self.win.flip(clearBuffer=True)
    def deg2pix_pos(self,deg):
        deg=np.array(deg)
        pix=self.d_cm*np.tan(np.radians(deg))*self.h_pix/self.h_cm
        pix=pix+self.offset
        return pix.astype(np.int64)
        
    def deg2pix_size(self,deg):
        deg=np.array(deg)
        pix=self.d_cm*np.tan(np.radians(deg))*self.h_pix/self.h_cm
        return pix.astype(np.int64)
        
    def pix2deg_pos(self,pix):
        pix=np.array(pix)
        pix=pix-self.offset
        deg=np.degrees(np.arctan(pix*self.h_cm/self.h_pix/self.d_cm))
        return deg
        
    def pix2deg_size(self,pix):
        pix=np.array(pix)
        deg=np.degrees(np.arctan(pix*self.h_cm/self.h_pix/self.d_cm))
        return deg
        
    def WaitKeys(self,keys=['space','return','escape'] ):
        return not bool (set(keys) & set(event.getKeys()))    
        
    def Dot(self,pos=[0,0],radius=10,color=[0,0,0]):
        dot=visual.Circle(self.win,radius=radius)
        dot.setLineColor(color=color,colorSpace='rgb255')
        dot.setFillColor(color=color,colorSpace='rgb255')
        dot.setPos(pos)
        dot.setAutoDraw(False)
        return dot    
        
    def SetOrigin(self):
        StartText = visual.TextStim(self.win, text='Move the red dot to the origin and press the spacebar.', pos=(0, int(self.v_pix/2-15)),wrapWidth=1000,height=30,units='pix')
        myMouse = event.Mouse(visible=True)
        c_img=self.Dot([0,0],10,[255,0,0])
        while (self.WaitKeys()) & (not (myMouse.getPressed())[2]):
            StartText.draw()
            if (myMouse.getPressed())[0]:
                self.offset=myMouse.getPos()
                c_img.setPos(self.offset)
            c_img.draw()
            self.win.flip()
        h,v=self.offset
        self.hline.start=[self.hline.start[0],v]
        self.hline.end=[self.hline.end[0],v]
        self.vline.start=[h,self.vline.start[1]]
        self.vline.end=[h,self.vline.end[1]]
        self.R10.pos=self.offset
        return self.offset

    def SetSpot(self,position=(0,0),radius=10):
        pos=self.deg2pix_pos(position)
        ori=self.origin+np.array(pos)*(1,-1)
        r=self.deg2pix_size(radius)
        lx,ly=ori-r
        rx,ry=ori+r
        self.fimg.image=self.fg.crop((lx,ly,rx,ry))
        self.fimg.setPos(pos)
        self.bimg.draw()
        self.fimg.draw()
        self.R10.draw()
        self.hline.draw()
        self.vline.draw()
        self.win.flip()
        
        
    def RedDot(self,position=[0,0]):
        pos=self.deg2pix_pos(position)
        img=self.Dot(pos,10,[255,0,0])
        myMouse = event.Mouse(visible=False)
        while self.WaitKeys() & (not (myMouse.getPressed())[2]):
            self.bimg.draw()
            img.draw()
            self.win.flip()
            
    def ByMouse(self,r=5,rmin=1,rmax=10,rstep=0.1):
        myMouse = event.Mouse(visible=False)
        
        while  not (set([1]) & set(myMouse.getPressed())):  
            pos=self.pix2deg_pos(myMouse.getPos())
            wheel_dX, wheel_dY = myMouse.getWheelRel()
            if wheel_dY !=0:
                r+=wheel_dY*rstep
                if r > rmax:r = rmax
                if r < rmin:r = rmin
            self.SetSpot(position=pos,radius=r)        
            

if __name__ == '__main__':
    sp=Spot('testMonitor',ScreenIndex=0,bg_brightness=0.5,bg_monochrome=True,bg_bokeh=8)
    sp.Ready("Ready, press any key to start !")
    sp.SetOrigin()
    sp.ByMouse()
    sp.win.close()
    core.quit()

