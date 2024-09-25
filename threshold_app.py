import streamlit as st
from PIL import Image, ImageOps
import numpy as np
import cv2

def apply_threshold(image, threshold):
    return image.point(lambda x: 255 if x > threshold else 0, mode='1')

def apply_canny(image, threshold1, threshold2):
    image_np = np.array(image)
    edges = cv2.Canny(image_np, threshold1, threshold2)
    return Image.fromarray(edges)

def mirror_image(image):
    return ImageOps.mirror(image)

def main():
    st.title("Image Processing App")

    uploaded_file = st.file_uploader("Choose an image...", type=["jpg", "jpeg", "png"])

    if uploaded_file is not None:
        image = Image.open(uploaded_file).convert('L')  # Convert to grayscale

        col1, col2 = st.columns([3, 1])
        with col2:
            mirror_images = st.checkbox("Mirror Images")

        if mirror_images:
            image = mirror_image(image)

        with col1:
            imagePrev = image.resize((image.width // 2, image.height // 2))  # Resize to 50%
            st.image(imagePrev, caption="Original (50%)" if not mirror_images else "Mirrored (50%)", use_column_width=True)

        if mirror_images:
            image = mirror_image(image)
            imagePrev = image.resize((image.width // 2, image.height // 2))  # Resize to 50% again after mirroring

        threshold_percent = st.slider("Threshold (%)", 0, 100, 50)
        threshold = int(threshold_percent * 255 / 100)  # Convert percentage to 0-255 range

        threshold_image = apply_threshold(image, threshold)
        st.image(threshold_image, caption=f"Processed Image (Threshold: {threshold_percent}%)", use_column_width=True)

        st.text("Canny Edge Detection")
        threshold_range = st.slider("Threshold Range", 0, 255, (100, 200))
        threshold1, threshold2 = threshold_range

        canny_image = apply_canny(image, threshold1, threshold2)
        st.image(canny_image, caption=f"Canny Edge Detection with Morphological Opening (Threshold1: {threshold1}, Threshold2: {threshold2})", use_column_width=True)

if __name__ == "__main__":
    main()
