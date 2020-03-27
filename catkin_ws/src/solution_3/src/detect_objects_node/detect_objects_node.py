#!/usr/bin/env python
# -*- coding: utf8 -*-

# Title:        The Detect objects stack for state machine at StarLine competition
# File:         detect_objects_node.py
# Date:         2020-03-26
# Author:       Artur Golubtsov @goldarte
# Description:  Detect objects

import cv2
import numpy as np
import rospy
from cv_bridge import CvBridge
from sensor_msgs.msg import Image
from find_object_2d.msg import ObjectsStamped
from std_srvs.srv import Trigger, TriggerResponse
from dynamic_reconfigure.server import Server
from solution_3.cfg import dyn_detect_Config

class DynParams:

    default_dict = {
        "light_area":0.1,
        "stop_area":0.1,
        "red_area":0.2,
        "red_h_l":0,
        "red_h_h":30,
        "red_s_l":22,
        "red_s_h":203,
        "red_l_l":106,
        "red_l_h":255
    }

    def __init__(self):
        for key, value in self.default_dict.items():
            setattr(self, key, value)

cv_bridge = CvBridge()
dyn_params = DynParams()
last_image = None
last_image_cv2 = None
last_image_area = 0
last_objects = None
detected_objects = None
roi = None
area_dict = {}

def image_callback(msg):
    global last_image
    last_image = msg

def objects_callback(msg):
    global last_objects
    last_objects = msg
    rospy.loginfo(last_objects.objects.data)

def dyn_param_callback(config, level):
    global area_dict
    for key, value in config.items():
        setattr(dyn_params, key, value)
    area_dict['stop'] = dyn_params.stop_area
    area_dict['traffic_light'] = dyn_params.light_area
    return config

def detect_objects(event):
    global cv_bridge, last_objects, last_image, last_image_cv2, last_image_area, detected_objects, roi, detected_red
    if last_objects is None:
        rospy.loginfo('No objects msg')
        return

    if not last_objects.objects.data:
        rospy.loginfo('No objects')
        return

    if last_image is None:
        rospy.loginfo('No image msg')
        return

    last_image_cv2 = cv_bridge.imgmsg_to_cv2(last_image)
    last_image_area = last_image_cv2.shape[0]*last_image_cv2.shape[1]

    detected_objects = select_objects(last_objects.objects.data)
    roi, mask = get_red_mask(detected_objects, last_image_cv2, dyn_params)
    debug_image = draw_frames(detected_objects, last_image_cv2)
    detected_red = detect_red(mask, detected_objects, debug_image, dyn_params)

    image_message = cv_bridge.cv2_to_imgmsg(debug_image, "bgr8")
    #image_message = cv_bridge.cv2_to_imgmsg(debug_image, "mono8")

    image_message.header.stamp = rospy.Time.now()
    debug_pub.publish(image_message)

def select_objects(objects_array, sort_by = 'max_area'):
    objects = {}
    objects['stop'] = []
    objects['traffic_light'] = []
    for i in range(0, len(objects_array), 12):
        if objects_array[0] == 1.0:
            objects['stop'].append(objects_array[i+1:i+12])
        else:
            objects['traffic_light'].append(objects_array[i+1:i+12])
    selected_objects = {}
    selected_objects['stop'] = []
    selected_objects['traffic_light'] = []
    if objects:
        rospy.loginfo(objects)
        try:
            for key, value in objects.items():
                if value:
                    selected_objects[key] = sorted(value, key=lambda data: data[0]*data[1])[-1]
        except ValueError as e:
            rospy.logwarn(e)
    rospy.loginfo("Selected objects: {}".format(selected_objects))
    return selected_objects

def detect_stop_service(request):
    global detected_objects, last_image_area
    responce = TriggerResponse()
    if detected_objects['stop']:
        x,y,w,h = get_frame(detected_objects['stop'])
        object_area = w*h
        if object_area > dyn_params.stop_area*last_image_area:
            responce.success = True
            responce.message = "Stop sign detected!"
        else:
            responce.success = False
            responce.message = "Stop sign is detected, but small!"
    else:
        responce.success = False
        responce.message = "Stop sign is not detected!"
    return responce

def detect_light_service(request):
    global detected_objects, last_image_area, detected_red
    responce = TriggerResponse()
    if detected_objects:
        if detected_objects['traffic_light']:
            x,y,w,h = get_frame(detected_objects['traffic_light'])
            light_area = w*h
            if light_area > dyn_params.light_area*last_image_area:
                if detected_red:
                    responce.success = True
                    responce.message = "Traffic red light detected!"
                else:
                    responce.success = False
                    responce.message = "Traffic light detected, but not red!"
            else:
                responce.success = False
                responce.message = "Traffic light detected, but small!"
    else:
        responce.success = False
        responce.message = "Traffic light is not detected!"
    return responce

def homotography(x, y, m):
    xn = m[0]*x + m[3]*y + m[6]
    yn = m[1]*y + m[4]*x + m[7]
    w = m[2]*x + m[5]*y + m[8]
    xn /= w
    yn /= w
    return [xn, yn]

def get_frame(object_detected):
    if object_detected:
        width = int(object_detected[0])
        height = int(object_detected[1])
        m = object_detected[2:11]
        tl = homotography(0, 0, m)
        tr = homotography(width, 0, m)
        bl = homotography(0, height, m)
        br = homotography(width, height, m)
        L = [tl,tr,bl,br]
        ctr = np.array(L).reshape((-1,1,2)).astype(np.int32)
        return cv2.boundingRect(ctr)
    else:
        return [0,0,0,0]


def draw_frame(object_detected, cv2_image):
    if object_detected:
        color = (0, 0, 255)
        x, y, width, height = get_frame(object_detected)
        rectangled = cv2.rectangle(cv2_image, (x, y),
                    (x + width, y + height), color, 3)
        return rectangled
    else:
        return cv2_image

def draw_frames(objects, cv2_image):
    global last_image_area, area_dict
    result = cv2_image.copy()
    for key, value in objects.items():
        x,y,w,h = get_frame(value)
        if w*h > area_dict[key]*last_image_area:
            result = draw_frame(value, result)
    return result

def get_mask(object_detected, cv2_image, hl, hh, sl, sh, ll, lh):
    if object_detected:
        image = cv2_image.copy()
        x, y, w, h = get_frame(object_detected)
        cropped = image[y:y+h, x:x+w]
        # Convert BGR to HSV
        hsv = cv2.cvtColor(cropped, cv2.COLOR_BGR2HSV)

        # define range of red color in HSV
        lower_red = np.array([hl, sl, ll])
        upper_red = np.array([hh, sh, lh])

        # Threshold the HSV image to get only red colors
        mask = cv2.inRange(hsv, lower_red, upper_red)

        # Bitwise-AND mask and original image
        res = cv2.bitwise_and(cropped, cropped, mask = mask)
        mask = cv2.bitwise_not(mask)

        return res, mask
    else:
        return cv2_image, None


def get_red_mask(objects, cv2_image, params):
    return get_mask(objects['traffic_light'], cv2_image,
                    params.red_h_l, params.red_h_h, params.red_s_l, params.red_s_h, params.red_l_l, params.red_l_h,)

def detect_red(mask, objects, cv2_image, params):
    global last_image_area
    x,y,w,h=get_frame(objects['traffic_light'])
    if mask is not None and w*h > area_dict['traffic_light']*last_image_area:
        mask = cv2.bitwise_not(mask)
        im2,contours,hierarchy = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
        if len(contours) != 0:
            # find the biggest countour (c) by the area
            c = max(contours, key = cv2.contourArea)
            if cv2.contourArea(c) > params.red_area*w*h:
                cv2.drawContours(cv2_image, [c], -1, (0,255,0) , 2, offset=(x,y))
                return True
    return False


if __name__ == "__main__":
    rospy.init_node('object_detector')
    srv = Server(dyn_detect_Config, dyn_param_callback)

    image_sub_topic = rospy.get_param('~image_topic', 'test_image')
    rospy.loginfo("image_sub_topic: {}".format(image_sub_topic))

    debug_topic = rospy.get_param('~debug_topic', 'image_debug')
    rospy.loginfo("debug_topic: {}".format(debug_topic))

    objects_topic = rospy.get_param('~objects_topic', 'objectsStamped')
    rospy.loginfo("objects_topic: {}".format(objects_topic))

    image_sub = rospy.Subscriber(image_sub_topic, Image, image_callback)
    objects_sub = rospy.Subscriber(objects_topic, ObjectsStamped, objects_callback)
    debug_pub = rospy.Publisher(debug_topic, Image, queue_size=1)

    rospy.Service('detected_stop', Trigger, detect_stop_service)
    rospy.Service('detected_redlight', Trigger, detect_light_service)

    rospy.Timer(rospy.Duration(0.1), detect_objects)

    rospy.spin()
