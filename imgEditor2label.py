import streamlit as st
import numpy as np
import cv2
from PIL import Image
import subprocess

def threshold_and_smooth_image(image, threshold_value, smoothing_kernel_size, invert_image):
    # Convert the image to grayscale
    gray_image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    # Apply binary thresholding with the selected threshold value
    _, thresholded_image = cv2.threshold(gray_image, threshold_value, 255, cv2.THRESH_BINARY)

    # Apply smoothing using Gaussian blur with the selected kernel size
    smoothed_image = cv2.GaussianBlur(thresholded_image, (smoothing_kernel_size, smoothing_kernel_size), 0)

    # Invert the image if the option is selected
    if invert_image:
        smoothed_image = 255 - smoothed_image

    return smoothed_image

def print_image(file_path):
    command = f"brother_ql -b pyusb --model QL-570 -p usb://0x04f9:0x2028/000M6Z401370 print -l 62 \"{file_path}\""
    subprocess.run(command, shell=True)

# Title of the app
st.title('image editor for stickerPrinter')

# Upload the image
uploaded_image = st.file_uploader("Choose an image file (png/jpg/gif)", type=['png', 'jpg', 'gif'])

if uploaded_image is not None:
    # Read the uploaded image
    image = Image.open(uploaded_image).convert('RGB')
    image_np = np.array(image)

    # Sliders
    threshold_value = st.slider('Threshold Value', min_value=0, max_value=255, value=127)
    # smoothing_kernel_size = st.slider('Smoothing Kernel Size', min_value=1, max_value=9, value=3, step=2)
    smoothing_kernel_size = 3
    # Invert button
    invert_image = st.button('Invert Image')

    # Threshold and smooth the image with the selected values
    processed_image = threshold_and_smooth_image(image_np, threshold_value, smoothing_kernel_size, invert_image)

    # Display the images side by side
    col1, col2 = st.columns(2)
    col1.image(image_np, caption='Original Image', use_column_width=True)
    col2.image(processed_image, caption=f'Processed Image (Threshold: {threshold_value}, Smoothing Kernel: {smoothing_kernel_size})', use_column_width=True, channels='GRAY')

    # Print button
    if st.button('Print Processed Image'):
        # Save the processed image to a file
        file_path = 'processed_image.png'
        cv2.imwrite(file_path, processed_image)

        # Print the image using the provided function
        print_image(file_path)

        st.success('Image sent to printer!')

ft = """
<style>
a:link , a:visited{
color: #BFBFBF;  /* theme's text color hex code at 75 percent brightness*/
background-color: transparent;
text-decoration: none;
}

a:hover,  a:active {
color: #0283C3; /* theme's primary color*/
background-color: transparent;
text-decoration: underline;
}

#page-container {
  position: relative;
  min-height: 10vh;
}

footer{
    visibility:hidden;
}

.footer {
position: relative;
left: 0;
top:230px;
bottom: 0;
width: 100%;
background-color: transparent;
color: #808080; /* theme's text color hex code at 50 percent brightness*/
text-align: left; /* you can replace 'left' with 'center' or 'right' if you want*/
}
</style>

<div id="page-container">

<div class="footer">
<p style='font-size: 0.875em;'>Made with <a style='display: inline; text-align: left;' href="https://streamlit.io/" target="_blank">Streamlit</a><br 'style= top:3px;'>
with <img src="https://em-content.zobj.net/source/skype/289/red-heart_2764-fe0f.png" alt="heart" height= "10"/><a style='display: inline; text-align: left;' href="https://github.com/sape94" target="_blank"> by sape94</a></p>
</div>

</div>
"""
st.write(ft, unsafe_allow_html=True)