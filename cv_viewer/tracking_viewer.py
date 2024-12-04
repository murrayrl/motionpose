import cv2
import numpy as np

from cv_viewer.utils import *
import pyzed.sl as sl

#----------------------------------------------------------------------
#       2D VIEW
#----------------------------------------------------------------------
def cvt(pt, scale):
    '''
    Function that scales point coordinates
    '''
    out = [pt[0]*scale[0], pt[1]*scale[1]]
    return out

def render_sk(left_display, img_scale, obj, color, BODY_BONES):
    # Draw skeleton bones
    for part in BODY_BONES:
        kp_a = cvt(obj.keypoint_2d[part[0].value], img_scale)
        kp_b = cvt(obj.keypoint_2d[part[1].value], img_scale)
        # Check that the keypoints are inside the image
        if(kp_a[0] < left_display.shape[1] and kp_a[1] < left_display.shape[0] 
        and kp_b[0] < left_display.shape[1] and kp_b[1] < left_display.shape[0]
        and kp_a[0] > 0 and kp_a[1] > 0 and kp_b[0] > 0 and kp_b[1] > 0 ):
            cv2.line(left_display, (int(kp_a[0]), int(kp_a[1])), (int(kp_b[0]), int(kp_b[1])), color, 1, cv2.LINE_AA)

    # Skeleton joints
    for index, kp in enumerate(obj.keypoint_2d):
        cv_kp = cvt(kp, img_scale)
        if(cv_kp[0] < left_display.shape[1] and cv_kp[1] < left_display.shape[0]):
            cv2.circle(left_display, (int(cv_kp[0]), int(cv_kp[1])), 3, color, -1)
            # Assuming you have a list of joint names, add text next to the keypoint
            keypoint_index = index
            keypoint_name = keypoint_names.get(keypoint_index, "Unknown")
            text_position = (int(cv_kp[0]) + 5, int(cv_kp[1]) - 5)  # Position the text near the circle
            
            # Add text next to the circle to contain keypoint name
            cv2.putText(left_display,  keypoint_name, text_position, cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1, cv2.LINE_AA)


keypoint_names = {
    0: "PELVIS", 1: "NAVAL_SPINE", 2: "CHEST_SPINE", 3: "NECK", 4: "LEFT_CLAVICLE",
    5: "LEFT_SHOULDER", 6: "LEFT_ELBOW", 7: "LEFT_WRIST", 8: "LEFT_HAND", 9: "LEFT_HANDTIP",
    10: "LEFT_THUMB", 11: "RIGHT_CLAVICLE", 12: "RIGHT_SHOULDER", 13: "RIGHT_ELBOW", 14: "RIGHT_WRIST",
    15: "RIGHT_HAND", 16: "RIGHT_HANDTIP", 17: "RIGHT_THUMB", 18: "LEFT_HIP", 19: "LEFT_KNEE",
    20: "LEFT_ANKLE", 21: "LEFT_FOOT", 22: "RIGHT_HIP", 23: "RIGHT_KNEE", 24: "RIGHT_ANKLE",
    25: "RIGHT_FOOT", 26: "HEAD", 27: "NOSE", 28: "LEFT_EYE", 29: "LEFT_EAR", 30: "RIGHT_EYE",
    31: "RIGHT_EAR", 32: "LEFT_HEEL", 33: "RIGHT_HEEL"
}


def render_2D(left_display, img_scale, objects, is_tracking_on, body_format):
    '''
    Parameters
        left_display (np.array): numpy array containing image data
        img_scale (list[float])
        objects (list[sl.ObjectData]) 
    '''
    overlay = left_display.copy()

    # Render skeleton joints and bones
    for obj in objects:
        if render_object(obj, is_tracking_on):
            if len(obj.keypoint_2d) > 0:
                color = generate_color_id_u(obj.id)
                if body_format == sl.BODY_FORMAT.BODY_18:
                    render_sk(left_display, img_scale, obj, color, sl.BODY_18_BONES)
                elif body_format == sl.BODY_FORMAT.BODY_34:
                    render_sk(left_display, img_scale, obj, color, sl.BODY_34_BONES)
                elif body_format == sl.BODY_FORMAT.BODY_38:
                    render_sk(left_display, img_scale, obj, color, sl.BODY_38_BONES) 

    cv2.addWeighted(left_display, 0.9, overlay, 0.1, 0.0, left_display)