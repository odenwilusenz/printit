import streamlit as st
import numpy as np
import cv2
from PIL import Image
import subprocess, os, base64
from st_clickable_images import clickable_images
import io

# Check if the invert_image state exists, if not, create it
if 'invert_image' not in st.session_state:
    st.session_state.invert_image = False


@st.cache_data
def load_thumbnails():
    thumbnails = []
    thumbnail_files = [f for f in os.listdir('temp/thumbnails/') if f.endswith(('.png', '.jpg', '.gif'))]
    for thumbnail_file in thumbnail_files:
        thumbnail_path = os.path.join('temp/thumbnails/', thumbnail_file)
        thumbnail = Image.open(thumbnail_path)
        thumbnails.append(thumbnail)
    return thumbnails

@st.cache_data
def threshold_and_smooth_image(image, threshold_value, smoothing_kernel_size, invert_image):
    gray_image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    _, thresholded_image = cv2.threshold(gray_image, threshold_value, 255, cv2.THRESH_BINARY)
    smoothed_image = cv2.GaussianBlur(thresholded_image, (smoothing_kernel_size, smoothing_kernel_size), 0)
    if invert_image:
        smoothed_image = 255 - smoothed_image
    return smoothed_image

def print_image(file_path):
    command = f"brother_ql -b pyusb --model QL-570 -p usb://0x04f9:0x2028/000M6Z401370 print -l 62 \"{file_path}\""
    subprocess.run(command, shell=True)

@st.cache_data
def image_to_data_url(image_input):
    if isinstance(image_input, np.ndarray): # NumPy array
        if len(image_input.shape) == 2 or image_input.shape[2] == 1: # Grayscale
            image_pil = Image.fromarray(image_input.astype('uint8'), mode='L')
        else: # Color
            image_pil = Image.fromarray(image_input.astype('uint8'))
        buffer = io.BytesIO()
        image_format = 'png'
        image_pil.save(buffer, format=image_format)
        image_data = buffer.getvalue()
    else: # File path
        with open(image_input, "rb") as image_file:
            image_data = image_file.read()
            image_format = os.path.splitext(image_input)[1].lstrip(".").lower()
    
    base64_image = base64.b64encode(image_data).decode()
    data_url = f"data:image/{image_format};base64,{base64_image}"
    return data_url


# Title of the app
st.title('image editor for stickerPrinter')

# Upload the image
uploaded_image = st.file_uploader("Choose an image file (png/jpg/gif)", type=['png', 'jpg', 'gif'])


if uploaded_image is not None:
    image = Image.open(uploaded_image).convert('RGB')
    image_np = np.array(image)
    threshold_value = st.slider('Threshold Value', min_value=0, max_value=255, value=127)
    smoothing_kernel_size = 3

    if 'invert_image' not in st.session_state:
        st.session_state.invert_image = False
        
    if st.button('Invert Image'):
        st.session_state.invert_image = not st.session_state.invert_image


    # Threshold and smooth the image with the selected values
    processed_image = threshold_and_smooth_image(image_np, threshold_value, smoothing_kernel_size, st.session_state.invert_image)

    original_image_data_url = image_to_data_url(image_np)
    processed_image_data_url = image_to_data_url(processed_image)

    col1, col2 = st.columns(2)

    original_image_data_url = image_to_data_url(image_np)
    clicked_original = clickable_images(
        [original_image_data_url],
        titles=["Original Image"],
        div_style={"display": "flex", "justify-content": "center"},
        img_style={"margin": "5px", "height": "200px"},
    )

    processed_image_data_url = image_to_data_url(processed_image) # Using processed_image directly
    clicked_processed = clickable_images(
        [processed_image_data_url],
        titles=[f'Processed Image (Threshold: {threshold_value}, Smoothing Kernel: {smoothing_kernel_size})'],
        div_style={"display": "flex", "justify-content": "center"},
        img_style={"margin": "5px", "height": "200px"},
    )

    
    if clicked_original > -1:
        original_file_path = uploaded_image.name
        print_image(original_file_path)
        st.success(f'Original image sent to printer!')

    if clicked_processed > -1:
        adapted_file_path = os.path.join('temp/', os.path.basename(uploaded_image.name).split('.')[0] + '_adapted.png')
        cv2.imwrite(adapted_file_path, processed_image)
        print_image(adapted_file_path)
        st.success(f'Processed image sent to printer and saved as {adapted_file_path}!')


# Get the full paths of image files in the "temp/" folder
image_files_full_paths = [os.path.join('temp/', f) for f in os.listdir('temp/') if f.endswith(('.png', '.jpg', '.gif'))]

# Sort the image files by last modification time, then reverse the order
image_files_full_paths.sort(key=os.path.getmtime, reverse=True)

# Extract the filenames from the sorted full paths
image_files = [os.path.basename(image_file) for image_file in image_files_full_paths]

# Generate the data URLs for the sorted image files
image_data_urls = [image_to_data_url(image_file) for image_file in image_files_full_paths]
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
    clicked_image_path = image_files_full_paths[clicked]
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