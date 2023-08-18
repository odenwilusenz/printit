import streamlit as st
import numpy as np
import cv2
from PIL import Image
import subprocess, os, base64
from st_clickable_images import clickable_images

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

@st.cache_data
def load_thumbnails():
    thumbnails = []
    thumbnail_files = [f for f in os.listdir('temp/thumbnails/') if f.endswith(('.png', '.jpg', '.gif'))]
    for thumbnail_file in thumbnail_files:
        thumbnail_path = os.path.join('temp/thumbnails/', thumbnail_file)
        thumbnail = Image.open(thumbnail_path)
        thumbnails.append(thumbnail)
    return thumbnails

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
        # Save the processed image
        file_path = 'temp/processed_image.png'
        cv2.imwrite(file_path, processed_image)

        # Create and save the thumbnail
        thumbnail_path = 'temp/thumbnails/processed_image_thumbnail.png'
        image_pil = Image.fromarray(processed_image)
        thumbnail_size = (100, 100)
        image_pil.thumbnail(thumbnail_size)
        image_pil.save(thumbnail_path)

        # Print the image using the provided function
        print_image(file_path)

        st.success('Image sent to printer!')
def image_to_data_url(image_path):
    with open(image_path, "rb") as image_file:
        base64_image = base64.b64encode(image_file.read()).decode()
        image_format = os.path.splitext(image_path)[1].lstrip(".").lower()
        data_url = f"data:image/{image_format};base64,{base64_image}"
        return data_url

# Get the list of image files in the "temp/" folder
image_files = [f for f in os.listdir('temp/') if f.endswith(('.png', '.jpg', '.gif'))]
image_data_urls = [image_to_data_url(os.path.join('temp/', image_file)) for image_file in image_files]
image_titles = [f"{image_file}" for image_file in image_files]

# Display the clickable thumbnails
clicked = clickable_images(
    image_data_urls,
    titles=image_titles,
    div_style={"display": "flex", "justify-content": "center", "flex-wrap": "wrap"},
    img_style={"margin": "5px", "height": "200px"},
)

# Handle the click event
if clicked > -1:
    clicked_image_path = os.path.join('temp/', image_files[clicked])
    print_image(clicked_image_path)
    st.success(f'Image {image_files[clicked]} sent to printer!')





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
made at 
<a style='display: inline; text-align: left;' href="https://wiki.sgmk-ssam.ch/wiki/PASAR_SENGGOL" target="_blank"> at the passar senggol</a> , 
<a style='display: inline; text-align: left;' href="https://github.com/5shekel/brother_ql_web" target="_blank"> (source)</a></p>
</div>

</div>
"""
st.write(ft, unsafe_allow_html=True)