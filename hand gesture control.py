
import cv2
import mediapipe as mp
import pydirectinput
import math
import time

pydirectinput.FAILSAFE = False
pydirectinput.PAUSE = 0.



KEY_LEFT = "a"
KEY_RIGHT = "d"
KEY_ACCEL = "w"
KEY_BRAKE = "s"
KEY_NITRO = "space"

STEER_ANGLE_THRESHOLD = 10      
SHARP_STEER_ANGLE = 35          

NITRO_COOLDOWN = 0.0           
FRAME_WIDTH = 640               
FRAME_HEIGHT = 360

STEER_EMA_ALPHA = 0.35  
GRADUAL_STEER_DUTY_LOW = 0.3  
GRADUAL_STEER_DUTY_HIGH = 1.0  
STEER_PULSE_CYCLE = 0.10        

mp_hands = mp.solutions.hands
mp_draw = mp.solutions.drawing_utils

hands_detector = mp_hands.Hands(
    static_image_mode=False,
    max_num_hands=2,
    min_detection_confidence=0.55,  
    min_tracking_confidence=0.45,   
    model_complexity=0,             
)

key_state = {
    KEY_LEFT: False,
    KEY_RIGHT: False,
    KEY_ACCEL: False,
    KEY_BRAKE: False,
    KEY_NITRO: False,
}


def set_key(key, should_be_down):
    """Key ko sirf tab press/release karo jab state change ho raha ho."""
    if should_be_down and not key_state[key]:
        pydirectinput.keyDown(key)
        key_state[key] = True
    elif not should_be_down and key_state[key]:
        pydirectinput.keyUp(key)
        key_state[key] = False


def release_all_keys():
    for k in key_state:
        set_key(k, False)


def fingers_extended(landmarks):
    """
    Har landmark list (21 points) ke liye 5 fingers ka open/closed state
    return karta hai: [thumb, index, middle, ring, pinky] -> True/False
    """
    lm = landmarks.landmark
    fingers = []


    thumb_tip = lm[4]
    thumb_ip = lm[3]
    pinky_mcp = lm[17]
    dist_tip = math.hypot(thumb_tip.x - pinky_mcp.x, thumb_tip.y - pinky_mcp.y)
    dist_ip = math.hypot(thumb_ip.x - pinky_mcp.x, thumb_ip.y - pinky_mcp.y)
    fingers.append(dist_tip > dist_ip * 1.15)

    tips_pips = [(8, 6), (12, 10), (16, 14), (20, 18)]
    for tip_idx, pip_idx in tips_pips:
        fingers.append(lm[tip_idx].y < lm[pip_idx].y)

    return fingers  # [thumb, index, middle, ring, pinky]


def classify_hand(fingers):
    """
    fingers = [thumb, index, middle, ring, pinky] booleans
    Returns: "open", "fist", "thumb_only", "other"
    """
    thumb, index, middle, ring, pinky = fingers
    
    if (index and middle and ring and pinky) or fingers.count(True) >= 4:
        return "open"
        
    if thumb and not (index or middle or ring or pinky):
        return "thumb_only"
        
    if fingers.count(True) <= 1:
        return "fist"
        
    return "other"


def hand_center(landmarks):
    """Palm ka approximate center (wrist + middle_mcp ka average)."""
    lm = landmarks.landmark
    cx = (lm[0].x + lm[9].x) / 2
    cy = (lm[0].y + lm[9].y) / 2
    return cx, cy


def main():
    cap = cv2.VideoCapture(0)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, FRAME_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_HEIGHT)
    cap.set(cv2.CAP_PROP_FPS, 60)           
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)     

    # EMA state for smooth steering
    smoothed_angle = 0.0

    print("Hand Gesture Controller shuru ho gaya. Emulator window active rakho.")
    print("Band karne ke liye webcam window pe 'q' dabao.")

    while True:
        success, frame = cap.read()
        if not success:
            break

        frame = cv2.flip(frame, 1)  
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        result = hands_detector.process(rgb)

        action_text = "No hands detected"
        hands_info = [] 

        if result.multi_hand_landmarks:
            for hand_landmarks in result.multi_hand_landmarks:
                mp_draw.draw_landmarks(frame, hand_landmarks, mp_hands.HAND_CONNECTIONS)
                fingers = fingers_extended(hand_landmarks)
                hand_class = classify_hand(fingers)
                cx, cy = hand_center(hand_landmarks)
                hands_info.append((cx, cy, hand_class))

        if len(hands_info) == 0:
            release_all_keys()
            action_text = "No hands - PAUSED"

        else:
            classes = [h[2] for h in hands_info]

            if "open" in classes:
                # -------- BRAKE --------
                set_key(KEY_BRAKE, True)
                set_key(KEY_ACCEL, False)
                set_key(KEY_LEFT, False)
                set_key(KEY_RIGHT, False)
                set_key(KEY_NITRO, False)
                action_text = "BRAKE (S)"

            else:
              
                set_key(KEY_BRAKE, False)
                set_key(KEY_ACCEL, True)

                # Check Nitro: are both hands thumb_only?
                is_nitro = (len(hands_info) == 2 and classes.count("thumb_only") == 2)
                set_key(KEY_NITRO, is_nitro)

                if len(hands_info) == 2:
                    # -------- STEERING (dono hath = steering wheel) --------
                
                    hands_info = sorted(hands_info, key=lambda h: h[0])

                    (x1, y1, _), (x2, y2, _) = hands_info[0], hands_info[1]
                    dx = x2 - x1
                    dy = y2 - y1
                    raw_angle = math.degrees(math.atan2(dy, dx))

                    # === EMA SMOOTHING ===
                    smoothed_angle = (STEER_EMA_ALPHA * raw_angle
                                      + (1.0 - STEER_EMA_ALPHA) * smoothed_angle)
                    angle = smoothed_angle
                    abs_angle = abs(angle)

                    if abs_angle < STEER_ANGLE_THRESHOLD:
                        # Dead zone
                        set_key(KEY_LEFT, False)
                        set_key(KEY_RIGHT, False)
                        action_text = f"STRAIGHT (angle {angle:.1f})"
                    else:
                        # Smooth duty cycle calculate 
                        if abs_angle >= SHARP_STEER_ANGLE:
                            steer_duty = 1.0  # full sharp turn
                        else:
                            # linearly interpolate between low and high duty
                            t = (abs_angle - STEER_ANGLE_THRESHOLD) / (SHARP_STEER_ANGLE - STEER_ANGLE_THRESHOLD)
                            steer_duty = GRADUAL_STEER_DUTY_LOW + (GRADUAL_STEER_DUTY_HIGH - GRADUAL_STEER_DUTY_LOW) * t

                        # Pulse based on time (chhoti window = fast response)
                        in_cycle = time.time() % STEER_PULSE_CYCLE
                        should_steer = in_cycle < (steer_duty * STEER_PULSE_CYCLE)

                        if angle > 0:  # Turn Right
                            set_key(KEY_LEFT, False)
                            set_key(KEY_RIGHT, should_steer)
                            type_text = "SHARP RIGHT" if steer_duty == 1.0 else f"SMOOTH RIGHT ({steer_duty*100:.0f}%)"
                            action_text = f"{type_text} (angle {angle:.1f})"
                        else:  # Turn Left
                            set_key(KEY_RIGHT, False)
                            set_key(KEY_LEFT, should_steer)
                            type_text = "SHARP LEFT" if steer_duty == 1.0 else f"SMOOTH LEFT ({steer_duty*100:.0f}%)"
                            action_text = f"{type_text} (angle {angle:.1f})"

                    if is_nitro:
                        action_text += " + NITRO!"

                else:
                
                    set_key(KEY_LEFT, False)
                    set_key(KEY_RIGHT, False)
                    set_key(KEY_NITRO, False)
                    action_text = "Only 1 hand - straight"

        cv2.putText(frame, action_text, (20, 40), cv2.FONT_HERSHEY_SIMPLEX,
                    0.9, (0, 255, 0), 2)
        cv2.imshow("Hand Gesture Controller (press q to quit)", frame)

        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

    release_all_keys()
    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()