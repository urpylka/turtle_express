#!/usr/bin/env python3
# -*- coding: utf8 -*-

# Title:        The detect objects stack for state machine at StarLine competition
# File:         detect_objects.py
# Date:         2020-03-26
# Author:       Artem Smirnov @urpylka, Artur Golubtsov @goldarte
# Description:  Detect objects

class DetectObjects(object):

    def __init__(self):
        # Stop robot when catched Ctrl-C or failure
        rospy.on_shutdown(self.cancelGoal)


    def detectedStopSign(self):
        return True # or False


    def detectedSemaphore(self):
        return True # or False
