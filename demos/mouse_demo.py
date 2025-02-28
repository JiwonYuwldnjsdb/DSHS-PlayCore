import cv2
import mediapipe as mp
import pyautogui
import time
import math

# ==========================
# 1. PyAutoGUI Configuration
# ==========================

# Disable PyAutoGUI's default pause after each call
pyautogui.PAUSE = 0

# (Optional) Disable PyAutoGUI's fail-safe
# WARNING: Disabling fail-safe removes the ability to abort the script by moving the cursor to a screen corner.
pyautogui.FAILSAFE = False

# ==========================
# 2. Initialize MediaPipe
# ==========================

mp_hands = mp.solutions.hands

# ==========================
# 3. Initialize Webcam
# ==========================

cap = cv2.VideoCapture(0)

# Set a lower resolution for faster processing
FRAME_WIDTH = 80  # Reduced from 320 for faster processing
FRAME_HEIGHT = 60  # Reduced from 240 for faster processing
cap.set(cv2.CAP_PROP_FRAME_WIDTH, FRAME_WIDTH)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_HEIGHT)

# ==========================

# 4. Screen Dimensions
# ==========================

screen_width, screen_height = pyautogui.size()

# ==========================
# 5. Define Scaling and ROI
# ==========================

SCALING_FACTOR = 3.0  # Increased for more responsive cursor movement

# Define Region of Interest (ROI) in the camera frame (central 50%)
ROI_X_MIN = 0.25  # 25% from the left
ROI_X_MAX = 0.75  # 75% from the left
ROI_Y_MIN = 0.25  # 25% from the top
ROI_Y_MAX = 0.75  # 75% from the top

# ==========================
# 6. Initialize State Variables
# ==========================

prev_screen_x, prev_screen_y = 0, 0  # Previous cursor positions for smoothing

# EMA Smoothing Factors
alpha = 0.2  # Smoothing factor for EMA

# ==========================
# 8. Initialize MediaPipe Hands
# ==========================

def angle_between_three_points(A, B, C):
    A = (A.x, A.y)
    B = (B.x, B.y)
    C = (C.x, C.y)
    
    BA = (A[0] - B[0], A[1] - B[1])
    BC = (C[0] - B[0], C[1] - B[1])

    dot_product = BA[0] * BC[0] + BA[1] * BC[1]

    mag_BA = math.sqrt(BA[0]**2 + BA[1]**2)
    mag_BC = math.sqrt(BC[0]**2 + BC[1]**2)

    if mag_BA == 0 or mag_BC == 0:
        return None

    cos_angle = dot_product / (mag_BA * mag_BC)

    cos_angle = max(min(cos_angle, 1.0), -1.0)

    angle_radians = math.acos(cos_angle)
    angle_degrees = math.degrees(angle_radians)

    return angle_degrees

with mp_hands.Hands(
    static_image_mode=False,
    max_num_hands=1,  # Track only one hand
    min_detection_confidence=0.4,  # Further lowered for speed
    min_tracking_confidence=0.4   # Further lowered for speed
) as hands:
    print("Virtual Mouse is running...")

    while True:
        success, frame = cap.read()
        if not success:
            print("Failed to grab frame")
            break

        # Flip the frame horizontally for natural (mirror) viewing
        frame = cv2.flip(frame, 1)

        # Convert the BGR image to RGB as MediaPipe requires RGB
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        # Process the frame with MediaPipe
        results = hands.process(frame_rgb)

        if results.multi_hand_landmarks:
            hand_landmarks = results.multi_hand_landmarks[0]  # Only one hand

            # ==========================
            # Determine Finger States
            # ==========================

            # Simple thumb extension check based on x-coordinates
            # This works for right hand; invert comparison for left hand
            
            # ==========================
            # Click Logic: Pinch Gesture
            # ==========================
            
            # Perform click when thumb is not extended and other fingers are folded
            if angle_between_three_points(hand_landmarks.landmark[8], hand_landmarks.landmark[5], hand_landmarks.landmark[12]) < 10:
                pyautogui.mouseDown()
            else:
                pyautogui.mouseUp()

            # ==========================
            # Mouse Movement Based on Index Finger
            # ==========================

            # Use index finger tip for cursor movement
            index_tip = hand_landmarks.landmark[5]

            # Apply ROI by restricting the normalized coordinates
            roi_x = min(max(index_tip.x, ROI_X_MIN), ROI_X_MAX)
            roi_y = min(max(index_tip.y, ROI_Y_MIN), ROI_Y_MAX)

            # Normalize the ROI area to [0,1]
            normalized_x = (roi_x - ROI_X_MIN) / (ROI_X_MAX - ROI_X_MIN)
            normalized_y = (roi_y - ROI_Y_MIN) / (ROI_Y_MAX - ROI_Y_MIN)

            # Apply scaling factor
            scaled_x = normalized_x * SCALING_FACTOR
            scaled_y = normalized_y * SCALING_FACTOR

            # Clamp the scaled values to [0,1]
            scaled_x = min(max(scaled_x, 0), 1)
            scaled_y = min(max(scaled_y, 0), 1)

            # Convert to screen coordinates
            screen_x = scaled_x * screen_width
            screen_y = scaled_y * screen_height

            # ==========================
            # Apply Exponential Moving Average (EMA) Smoothing
            # ==========================

            smooth_x = alpha * screen_x + (1 - alpha) * prev_screen_x
            smooth_y = alpha * screen_y + (1 - alpha) * prev_screen_y

            # Update previous positions
            prev_screen_x, prev_screen_y = smooth_x, smooth_y

            # Move the mouse cursor with no delay
            try:
                pyautogui.moveTo(int(smooth_x), int(smooth_y), duration=0)
            except pyautogui.FailSafeException:
                pass  # Ignore fail-safe exception if cursor reaches screen corner

        # Optional: Reduce CPU usage with a short sleep
        # time.sleep(0.005)  # Sleep for 5ms

    # ==========================
    # 9. Cleanup
    # ==========================

    cap.release()
    print("Virtual Mouse has been terminated.")