#!/usr/bin/env/python
# File name   : FPV.py
# Website     : www.Adeept.com
# Author      : Adeept
# Date		  : 2025/03/12


import cv2
import zmq
import base64
from picamera2 import Picamera2
import libcamera
import io

import argparse
import imutils
import PID
import Kalman_Filter as Kalman_filter
import RobotLight as robotLight
import datetime
import Move as move
import Switch as switch
import numpy as np
import RPIservo

pid = PID.PID()
pid.SetKp(0.5)
pid.SetKd(0)
pid.SetKi(0)
Y_lock = 0
X_lock = 0
tor = 17
FindColorMode = 0
WatchDogMode = 0
UltraData = 3
ws2812 = robotLight.Adeept_SPI_LedPixel(16, 255)


Dv = -1  # Directional variable
CVRun = 1
FindLineMode = 0
linePos_1 = 440
linePos_2 = 380
lineColorSet = 255
frameRender = 0
findLineError = 20
Threshold = 80
findLineMove = 1
tracking_servo_status = 0
FLCV_Status = 0
turn_speed = 35
scGear = RPIservo.ServoCtrl()
scGear.moveInit()
Tracking_sc = RPIservo.ServoCtrl()
Tracking_sc.moveInit()
colorUpper = np.array([44, 255, 255])  # 1
colorLower = np.array([24, 100, 100])  # 1

hflip = 0  # Video flip horizontally: 0 or 1
vflip = 0  # Video vertical flip: 0/1

def map(input, in_min, in_max, out_min, out_max):
    return (input - in_min) / (in_max - out_min) * (out_max - out_min) + out_min


def findLineCtrl(posInput, setCenter): 
    global findLineMove,tracking_servo_status,FLCV_Status

    if FLCV_Status == 0:    
        scGear.moveAngle(0, -20) 
        tracking_servo_status = 3
        FLCV_Status = 1
    if posInput != None and findLineMove == 1:
        if posInput > 480: 
            if(tracking_servo_status != 1):
                move.move(40, 1, "rotate-right") 
                tracking_servo_status = 1 

        elif posInput < 180:
            if(tracking_servo_status != -1):
                move.move(40, 1, "rotate-left")  
                tracking_servo_status = -1  
                    
        else:
            if(tracking_servo_status != 0):
                move.move(40, 1, "mid") 
                tracking_servo_status = 0 
            
    else:
        move.motorStop() 
        if tracking_servo_status == -1 :
            move.move(50, 1, "rotate-left") 

        elif tracking_servo_status == 1 : 
            move.move(50, 1, "rotate-right") 
            
        else :
            tracking_servo_status = 3 


def cvFindLine(frame_image):
    frame_findline = cv2.cvtColor(frame_image, cv2.COLOR_BGR2GRAY)
    retval, frame_findline = cv2.threshold(frame_findline, Threshold, 255, cv2.THRESH_BINARY)
    frame_findline = cv2.erode(frame_findline, None, iterations=2)
    frame_findline = cv2.dilate(frame_findline, None, iterations=2)
    colorPos_1 = frame_findline[linePos_1]
    colorPos_2 = frame_findline[linePos_2]
    try:
        lineColorCount_Pos1 = np.sum(colorPos_1 == lineColorSet)
        lineColorCount_Pos2 = np.sum(colorPos_2 == lineColorSet)

        lineIndex_Pos1 = np.where(colorPos_1 == lineColorSet)
        lineIndex_Pos2 = np.where(colorPos_2 == lineColorSet)

        if lineIndex_Pos1 != []:
            if abs(lineIndex_Pos1[0][-1] - lineIndex_Pos1[0][0]) > 500:
                print("Tracking color not found")
                findLineMove = 0
            else:
                findLineMove = 1
        elif lineIndex_Pos2 != []:
            if abs(lineIndex_Pos2[0][-1] - lineIndex_Pos2[0][0]) > 500:
                print("Tracking color not found")
                findLineMove = 0
            else:
                findLineMove = 1

        if lineColorCount_Pos1 == 0:
            lineColorCount_Pos1 = 1
        if lineColorCount_Pos2 == 0:
            lineColorCount_Pos2 = 1

        left_Pos1 = lineIndex_Pos1[0][1]
        right_Pos1 = lineIndex_Pos1[0][lineColorCount_Pos1 - 2]
        center_Pos1 = int((left_Pos1 + right_Pos1) / 2)

        left_Pos2 = lineIndex_Pos2[0][1]
        right_Pos2 = lineIndex_Pos2[0][lineColorCount_Pos2 - 2]
        center_Pos2 = int((left_Pos2 + right_Pos2) / 2)

        center = int((center_Pos1 + center_Pos2) / 2)
    except:
        center = None
        pass

    findLineCtrl(center, 320)
    try:
        if lineColorSet == 255:
            cv2.putText(frame_image, ('Following White Line'), (30, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (128, 255, 128), 1,
                        cv2.LINE_AA)
            cv2.putText(frame_findline, ('Following White Line'), (30, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (128, 255, 128), 1,
                        cv2.LINE_AA)
        else:
            cv2.putText(frame_image, ('Following Black Line'), (30, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (128, 255, 128), 1,
                        cv2.LINE_AA)
            cv2.putText(frame_findline, ('Following Black Line'), (30, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (128, 255, 128), 1,
                        cv2.LINE_AA)

        if frameRender:
            cv2.line(frame_image, (left_Pos1, (linePos_1 + 30)), (left_Pos1, (linePos_1 - 30)), (255, 128, 64), 1)
            cv2.line(frame_image, (right_Pos1, (linePos_1 + 30)), (right_Pos1, (linePos_1 - 30)), (64, 128, 255), )
            cv2.line(frame_image, (0, linePos_1), (640, linePos_1), (255, 255, 64), 1)

            cv2.line(frame_image, (left_Pos2, (linePos_2 + 30)), (left_Pos2, (linePos_2 - 30)), (255, 128, 64), 1)
            cv2.line(frame_image, (right_Pos2, (linePos_2 + 30)), (right_Pos2, (linePos_2 - 30)), (64, 128, 255), 1)
            cv2.line(frame_image, (0, linePos_2), (640, linePos_2), (255, 255, 64), 1)

            cv2.line(frame_image, ((center - 20), int((linePos_1 + linePos_2) / 2)),
                     ((center + 20), int((linePos_1 + linePos_2) / 2)), (0, 0, 0), 1)
            cv2.line(frame_image, ((center), int((linePos_1 + linePos_2) / 2 + 20)),
                     ((center), int((linePos_1 + linePos_2) / 2 - 20)), (0, 0, 0), 1)
        else:
            cv2.line(frame_findline, (left_Pos1, (linePos_1 + 30)), (left_Pos1, (linePos_1 - 30)), (255, 128, 64), 1)
            cv2.line(frame_findline, (right_Pos1, (linePos_1 + 30)), (right_Pos1, (linePos_1 - 30)), (64, 128, 255), 1)
            cv2.line(frame_findline, (0, linePos_1), (640, linePos_1), (255, 255, 64), 1)

            cv2.line(frame_findline, (left_Pos2, (linePos_2 + 30)), (left_Pos2, (linePos_2 - 30)), (255, 128, 64), 1)
            cv2.line(frame_findline, (right_Pos2, (linePos_2 + 30)), (right_Pos2, (linePos_2 - 30)), (64, 128, 255), 1)
            cv2.line(frame_findline, (0, linePos_2), (640, linePos_2), (255, 255, 64), 1)

            cv2.line(frame_findline, ((center - 20), int((linePos_1 + linePos_2) / 2)),
                     ((center + 20), int((linePos_1 + linePos_2) / 2)), (0, 0, 0), 1)
            cv2.line(frame_findline, ((center), int((linePos_1 + linePos_2) / 2 + 20)),
                     ((center), int((linePos_1 + linePos_2) / 2 - 20)), (0, 0, 0), 1)
    except:
        pass

    return frame_findline


class FPV:
    kalman_filter_X = Kalman_filter.Kalman_filter(0.01, 0.1)
    kalman_filter_Y = Kalman_filter.Kalman_filter(0.01, 0.1)
    P_direction = 1
    T_direction = -1 
    P_servo = 1
    T_servo = 0
    P_anglePos = 0
    T_anglePos = 0
    cameraDiagonalW = 64
    cameraDiagonalH = 48
    videoW = 640
    videoH = 480
    Y_lock = 0
    X_lock = 0
    tor = 17

    def __init__(self):
        self.frame_num = 0
        self.fps = 0
        self.colorUpper = (44, 255, 255)
        self.colorLower = (24, 100, 100)

    def SetIP(self, invar):
        self.IP = invar

    def FindColor(self, invar):
        global FindColorMode
        FindColorMode = invar
        if not FindColorMode:
            scGear.moveAngle(1, 0)
            scGear.moveAngle(0, 0)

    def WatchDog(self, invar):
        global WatchDogMode
        WatchDogMode = invar

    def UltraData(self, invar):
        global UltraData
        UltraData = invar

    def setExpCom(self, invar): 
        if invar > 25:
            invar = 25
        elif invar < -25:
            invar = -25
        else:
            camera.exposure_compensation = invar

    def defaultExpCom(self): 
        camera.exposure_compensation = 0

    def colorFindSet(self, invarH, invarS, invarV):
        global colorUpper, colorLower
        HUE_1 = invarH + 15
        HUE_2 = invarH - 15
        if HUE_1 > 180:
            HUE_1 = 180
        if HUE_2 < 0:
            HUE_2 = 0

        SAT_1 = invarS + 150
        SAT_2 = invarS - 150
        if SAT_1 > 255:
            SAT_1 = 255
        if SAT_2 < 0:
            SAT_2 = 0

        VAL_1 = invarV + 150
        VAL_2 = invarV - 150
        if VAL_1 > 255:
            VAL_1 = 255
        if VAL_2 < 0:
            VAL_2 = 0

        colorUpper = np.array([HUE_1, SAT_1, VAL_1])
        colorLower = np.array([HUE_2, SAT_2, VAL_2])
        print('HSV_1:%d %d %d' % (HUE_1, SAT_1, VAL_1))
        print('HSV_2:%d %d %d' % (HUE_2, SAT_2, VAL_2))
        print(colorUpper)
        print(colorLower)
        
    def servoMove(ID, Dir, errorInput):
        if ID == 0:
            errorGenOut = FPV.kalman_filter_Y.kalman(errorInput)
            FPV.T_anglePos += 0.1 * (errorGenOut * Dir) * FPV.cameraDiagonalH / FPV.videoH
            if abs(errorInput) > FPV.tor:
                scGear.moveAngle(ID, FPV.T_anglePos)
                FPV.Y_lock = 0
            else:
                FPV.Y_lock = 1

    def changeMode(self, textPut):
        global modeText
        modeText = textPut

    def capture_thread(self, IPinver):
        ap = argparse.ArgumentParser()  # OpenCV initialization
        ap.add_argument("-b", "--buffer", type=int, default=64,
                        help="max buffer size")
        font = cv2.FONT_HERSHEY_SIMPLEX

        context = zmq.Context()
        footage_socket = context.socket(zmq.PAIR)
        print(IPinver)
        footage_socket.connect('tcp://%s:5555' % IPinver)

        avg = None
        motionCounter = 0
        # time.sleep(4)
        lastMovtionCaptured = datetime.datetime.now()

        with Picamera2() as camera:
            if not camera.is_open:
                raise RuntimeError('Could not start camera.')
            try:
                camera.start()
                stream = io.BytesIO()
            except Exception as e:
                print(f"\033[38;5;1mError:\033[0m\n{e}")
                print("\nPlease check whether the camera is connected well, and disable the \"legacy camera driver\" on raspi-config")
           
            preview_config = camera.preview_configuration
            preview_config.format = 'RGB888'   # 'XRGB8888', 'XBGR8888', 'RGB888', 'BGR888', 'YUV420'
            preview_config.size = (640, 480)
            preview_config.format = 'RGB888'   # 'XRGB8888', 'XBGR8888', 'RGB888', 'BGR888', 'YUV420'
            preview_config.transform = libcamera.Transform(hflip=hflip, vflip=vflip)
            preview_config.colour_space = libcamera.ColorSpace.Sycc()
            preview_config.buffer_count = 4
            preview_config.queue = True
            while True:
                frame_image = camera.capture_array()
                if frame_image is None:
                    continue
                timestamp = datetime.datetime.now()

                if FindLineMode:
                    frame_findline = cvFindLine(frame_image)
                    camera.exposure_mode = 'off'
                else:
                    camera.exposure_mode = 'auto'

                frame_image = cv2.cvtColor(frame_image, cv2.COLOR_RGB2BGR)
                if FindColorMode:
                    ####>>>OpenCV Start<<<####
                    hsv = cv2.cvtColor(frame_image, cv2.COLOR_BGR2HSV)
                    mask = cv2.inRange(hsv, colorLower, colorUpper)  # 1
                    mask = cv2.GaussianBlur(mask, (5, 5), 0)
                    mask = cv2.erode(mask, None, iterations=2)
                    mask = cv2.dilate(mask, None, iterations=2)
                    cnts = cv2.findContours(mask.copy(), cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)[-2]
                    center = None
                    if len(cnts) > 0:
                        cv2.putText(frame_image, 'Target Detected', (40, 60), font, 0.5, (255, 255, 255), 1, cv2.LINE_AA)

                        c = max(cnts, key=cv2.contourArea)
                        ((x, y), radius) = cv2.minEnclosingCircle(c)
                        M = cv2.moments(c)
                        center = (int(M["m10"] / M["m00"]), int(M["m01"] / M["m00"]))
                        X = int(x)
                        Y = int(y)
                        if radius > 10:
                            cv2.rectangle(frame_image, (int(x - radius), int(y + radius)), (int(x + radius), int(y - radius)),
                                          (255, 255, 255), 1)
                        print(f"X:{X} Y:{Y}")
                        error_Y = 240 - Y
                        FPV.servoMove(FPV.T_servo, FPV.T_direction, -error_Y)
                        print("11111")
                    else:
                        cv2.putText(frame_image, 'Target Detecting', (40, 60), font, 0.5, (255, 255, 255), 1, cv2.LINE_AA)
                        move.motorStop()

                if WatchDogMode:
                    gray = cv2.cvtColor(frame_image, cv2.COLOR_BGR2GRAY)
                    gray = cv2.GaussianBlur(gray, (21, 21), 0)

                    if avg is None:
                        print("[INFO] starting background model...")
                        avg = gray.copy().astype("float")
                        continue

                    cv2.accumulateWeighted(gray, avg, 0.5)
                    frameDelta = cv2.absdiff(gray, cv2.convertScaleAbs(avg))
                    thresh = cv2.threshold(frameDelta, 5, 255,
                                           cv2.THRESH_BINARY)[1]
                    thresh = cv2.dilate(thresh, None, iterations=2)
                    cnts = cv2.findContours(thresh.copy(), cv2.RETR_EXTERNAL,
                                            cv2.CHAIN_APPROX_SIMPLE)
                    cnts = imutils.grab_contours(cnts)
                    for c in cnts:
                        if cv2.contourArea(c) < 5000:
                            continue

                        (x, y, w, h) = cv2.boundingRect(c)
                        cv2.rectangle(frame_image, (x, y), (x + w, y + h), (128, 255, 0), 1)
                        motionCounter += 1
                        lastMovtionCaptured = timestamp

                if FindLineMode and not frameRender:
                    if cv2.imencode('.jpg', frame_findline)[0]:
                        buffer = cv2.imencode('.jpg', frame_findline)[1].tobytes()
                else:
                    if cv2.imencode('.jpg', frame_image)[0]:
                        buffer = cv2.imencode('.jpg', frame_image)[1].tobytes()
                jpg_as_text = base64.b64encode(buffer)
                footage_socket.send(jpg_as_text)

                stream.seek(0)
                stream.truncate()


if __name__ == '__main__':
    scGear = RPIservo.ServoCtrl()
    scGear.moveInit()
    Tracking_sc = RPIservo.ServoCtrl()
    Tracking_sc.start()
    CVRun = 1
    turn_speed = 35
    fpv = FPV()
    while 1:
        fpv.capture_thread('192.168.3.199')

    