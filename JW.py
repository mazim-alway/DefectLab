import streamlit as st
import cv2
import numpy as np
from PIL import Image

st.set_page_config(page_title="Smart Checker", layout="centered")

st.write("Copyright © 2026 LQH-M Series. All Rights Reserved.")

st.image("C:/Users/MME11253/Desktop/Personal (CONFIDENTIAL)/M@B@/25F2/murata logo.jpg", width=120)

st.title("Smart Checker [DefectLab]")

st.sidebar.title("Expert Support")
if st.sidebar.button("Ask Expert"):
    st.session_state["chat_mode"] = True

if st.session_state.get("chat_mode", False):
    st.subheader("Chat with PIC (via Teams)")
    user_message = st.text_input("You:", key="user_msg")
if st.button("Send"):
    st.write("You:", user_message)
    st.write("PIC:", "Thanks for reaching out, I’ll assist you.") # Here you would integrate with Teams API or Graph API

# Upload image
uploaded_file = st.file_uploader("Upload defect image", type=["jpg", "jpeg", "png"])

# Parameters
st.subheader("Scan Parameters")

orientation_angle_tolerance = st.slider("Wire Detection Angle Tolerance (deg)", 0, 45, 10)
defect_ratio_limit = st.slider("Visual Limit Criteria (%)", 0, 100, 9)

# Magnification dropdown
magnification = st.selectbox("Magnification", ["10x", "20x", "50x", "100x"])

# Calibration factors (example values, adjust to your microscope specs)
pixel_size_map = {
    "10x": 2.0,   # µm per pixel
    "20x": 1.0,
    "50x": 0.5,
    "100x": 0.25
}
pixel_size_um = pixel_size_map[magnification]
pixel_size_mm = pixel_size_um / 1000.0

# ROI dimensions in millimeters
roi_w_mm = st.number_input("ROI Width (mm)", value=5.0)
roi_h_mm = st.number_input("ROI Height (mm)", value=1.8)

# Convert ROI dimensions to pixels
roi_w_px = int(roi_w_mm / pixel_size_mm)
roi_h_px = int(roi_h_mm / pixel_size_mm)

st.write(f"ROI size in pixels: {roi_w_px} × {roi_h_px}")

if uploaded_file is not None:
    image = Image.open(uploaded_file)
    img_array = np.array(image)
    st.image(image, caption="Uploaded Image", use_column_width=True)

    img_array = np.array(image.convert("RGB"))
    hsv = cv2.cvtColor(img_array, cv2.COLOR_RGB2HSV) #covert to HSV

    # --- Automatic red box detection ---
    lower_red1 = np.array([0, 70, 50])
    upper_red1 = np.array([10, 255, 255])
    lower_red2 = np.array([170, 70, 50])
    upper_red2 = np.array([180, 255, 255])
    mask1 = cv2.inRange(hsv, lower_red1, upper_red1)
    mask2 = cv2.inRange(hsv, lower_red2, upper_red2)
    mask_red = cv2.bitwise_or(mask1, mask2)

    contours, _ = cv2.findContours(mask_red, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    if contours:
        # Use largest red contour as ROI
        c = max(contours, key=cv2.contourArea)
        x, y, w, h = cv2.boundingRect(c)
        roi = hsv[y:y+h, x:x+w]
        st.write(f"Auto-detected red box ROI: X={x}, Y={y}, W={w}, H={h}")
    else:
        # Fallback: use ROI dimensions in mm converted to pixels, starting at (0,0)
        roi = hsv[0:roi_h_px, 0:roi_w_px]
        st.write("No red box detected, using mm-based ROI.")

    img_copy = img_array.copy()
    cv2.rectangle(img_copy, (x, y), (x+w, y+h), (255, 0, 0), 2)
    st.image(img_copy, caption="Detected ROI", use_column_width=True)

    # --- Detect copper/yellowish wires in ROI ---
    lower_orange_yellow = np.array([15, 80, 80])   # Hue ~15°, orange-yellow
    upper_orange_yellow = np.array([35, 255, 255]) # Hue ~35°, yellow
    mask_wire = cv2.inRange(roi, lower_orange_yellow, upper_orange_yellow)

    # Detect contours of wire regions
    contours, _ = cv2.findContours(mask_wire, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    wire_area_px = 0
    roi_visual = cv2.cvtColor(roi, cv2.COLOR_HSV2RGB) # convert ROI back to RGB for visualization

    for cnt in contours:
        rect = cv2.minAreaRect(cnt)
        (cx, cy), (w, h), angle = rect

        # Normalize angle to [0, 180)
        if angle < -45:
            angle = angle + 90

        # Check if orientation is horizontal
        if abs(angle) < orientation_angle_tolerance:
            wire_area_px += cv2.contourArea(cnt)

    #Draw contour in green
    cv2.drawContours(roi_visual, [cnt], -1, (0, 255, 0), 2)

    #Optionally draw the rotated rectangle
    box = cv2.boxPoints(rect)
    box = np.int0(box)
    cv2.drawContours(roi_visual, [box], 0, (255, 0, 0), 2)

    # Show visualization of detected wires
    st.image(roi_visual, caption="Detected Wire Regions", use_column_width=True)

    roi_area_px = roi.shape[0] * roi.shape[1]

    # Convert to real units (mm²)
    wire_area_mm2 = wire_area_px * (pixel_size_mm ** 2)
    roi_area_mm2 = roi_area_px * (pixel_size_mm ** 2)

    defect_ratio = wire_area_mm2 / roi_area_mm2 * 100

    st.write(f"Area of wire exposed: {defect_ratio:.2f}%")

    if defect_ratio > defect_ratio_limit:
        st.error("Result: NG (Defect exceeds criteria)")
    else:
        st.success("Result: OK (Within criteria)")