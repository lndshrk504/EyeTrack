#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
iRecHS2 python class module

"""
from __future__ import division
from __future__ import unicode_literals

import pandas as pd
from io import StringIO
import numpy as np
import socket
import time


class iRecHS2(object):

    def state(self):
        return self.__state

    def connect(self):
        if self.__state=='disconnect':
            self.__client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.__client_socket.settimeout(5)
            self.__state='connect'
            try:
                self.__client_socket.connect((self.HOST,self.PORT))
            except OSError as msg:
                timeout=self.__client_socket.gettimeout()
                print('timeout {}sec'.format(timeout))
                print(msg)
                print('{}:{}'.format(self.HOST,self.PORT))
                self.__client_socket.close()
                self.__state='disconnect'

    # def __init__(self,host='localhost',port=35358):
    def __init__(self,host='192.168.1.50',port=35358):
        self.HOST=host
        self.PORT=port
        self.__remainStr=''
        self.__state='disconnect'
        self.connect()

    def send(self,h,v,s,cl):
        if (self.__state=='connect') or (self.__state=='receive'):
            gp='calibration\n'+'{t:>10.4f},{h:>6.2f},{v:>6.2f},{s:>6.2f}\n'.format(t=cl,h=h,v=v,s=s)
            self.__client_socket.sendall(bytes(gp,"ascii"))
    def start(self):
        if (self.__state=='connect'):
            self.__state='receive'
            self.__client_socket.sendall(b'start')

    def start_plus(self):
        if (self.__state=='connect'):
            self.__state='receive'
            self.__client_socket.sendall(b'start+')

    def stop(self,forceFlush=True):
        if (self.__state=='receive'):
            self.__remainStr=''
            self.__client_socket.sendall(b'stop')
            if forceFlush:
                time.sleep(0.1)
                self.get()     
            self.__state='connect'

    def close(self):
        self.stop()
        if (self.__state=='connect'):
            time.sleep(0.1)
            self.__client_socket.close()
            self.__state='disconnect'
        self.__remainStr=''

    def get(self):
        df=pd.DataFrame([],columns=['time','h','v','s','openness'])
        if (self.__state!='receive'):
            return df
        try:
            data=self.__client_socket.recv(4096)
        except OSError:
            self.__state='disconnect'
            self.__client_socket.close()
            return df
        if data==b'':
            self.__state='disconnect'
            self.__client_socket.close()
            return df
        s=self.__remainStr+data.decode()
        sp=s.split('\n')
        if (s[-1]!='\n'):
            self.__remainStr=sp.pop(-1)
        else:
            self.__remainStr=''
        for line in sp:        
            if (line.count(',')==4):
                df=df.append(pd.read_csv(StringIO(line),names=['time','h','v','s','openness'],dtype=float),ignore_index=True)
            else:
                continue
        return df

if __name__ == '__main__':

    # eye=iRecHS2('127.0.0.1') 
    eye=iRecHS2('192.168.1.50') 
    if eye.state()=='connect':
        print('---start---')
        eye.start()
        df=eye.get()
        print(df)
        print('---pause 5[sec]--')
        eye.stop()
        time.sleep(5)
        print('---data after start--')        
        eye.start()
        df=eye.get() 
        print(df)
        print('---close---')
        eye.close()
        print('---reconnect---')
        eye.connect()
        eye.start()
        df=eye.get()
        print(df)
        print('---close---')
        eye.close()
