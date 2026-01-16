#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
 Psychopy 1.9 & iRecHS2 sample program
 
 Run Psychopy & iRecHS2 on the same computer 
    # -> Server='localhost'
    -> Server='192.168.1.50'
 Run Psychopy & iRecHS2 on different computer
    -> Server='xxx.xxx.xxx.xxx' # iRecHS2 computer IP address
    
 Hit escape key or quit iRecHS2 to quit this program.
 
"""
from __future__ import division
from __future__ import unicode_literals
# Import key parts of the PsychoPy library:
from psychopy import visual,core,event
# Import iRecHS2 class
import irechs2 as irec


###EDIT HERE ###
# Server='localhost' # IP address of iRecHS2 computer
Server='192.168.1.50' # IP address of iRecHS2 computer
magnify=5
circle_radius=10
###EDIT HERE ###


def StartScreen(win,msg):
    StartText = visual.TextStim(win, text=msg, pos=(0, 0),wrapWidth=1000,height=30,units='pix')
    StartText.draw()
    win.flip()
    event.waitKeys()
    win.flip(clearBuffer=True)

def WaitEscape():
    keys=event.getKeys()
    for key in keys:
        if key=='escape':
            return  False
    return True

win = visual.Window(fullscr=False,units='pix', color='black')
x_size=win.size[0]/2-circle_radius
y_size=win.size[1]/2-circle_radius
circle_img=visual.Circle(win,radius=circle_radius)
msg = visual.TextStim(win, text='Hit escape key to quit.', pos=(0, 0),wrapWidth=1000,height=30,units='pix')

StartScreen(win,"Hit any key to start !")

eye=irec.iRecHS2(Server)
if eye.state()=='connect':
    eye.start()
#
# or use 
#  eye.start_plus()
# start_plus() sends data even when the eye is closed.
#
    while  ((eye.state()!='disconnect') & WaitEscape()):
        df=eye.get()
        if len(df)!=0:
            h=df['h'].mean()*magnify
            v=df['v'].mean()*magnify
            if ((abs(h)<x_size) & (abs(v)<y_size)):
                circle_img.setPos([h,v]) 
        msg.draw()
        circle_img.draw()
        win.flip()
    eye.close()
win.close()
core.quit()
