import streamlit as st
from PIL import Image
import subprocess
import os

def print_image(file_path):
    command = f"brother_ql -b pyusb --model QL-570 -p usb://0x04f9:0x2028/000M6Z401370 print -l 62 \"{file_path}\""
    subprocess.run(command, shell=True)

def save_uploaded_file(uploaded_file):
    temp_dir = "temp"
    os.makedirs(temp_dir, exist_ok=True)
    file_path = os.path.join(temp_dir, uploaded_file.name)

    # Check if a file with the same name exists
    if os.path.exists(file_path):
        # Option to overwrite or automatically rename
        if st.checkbox('File with same name exists. Overwrite?'):
            mode = 'wb'
        else:
            counter = 0
            original_name, extension = os.path.splitext(uploaded_file.name)
            while os.path.exists(file_path):
                counter += 1
                new_name = f"{original_name}_{counter:03}{extension}"
                file_path = os.path.join(temp_dir, new_name)
            mode = 'xb'
    else:
        mode = 'wb'

    try:
        with open(file_path, mode) as f:
            f.write(uploaded_file.getbuffer())
        return file_path
    except Exception as e:
        st.error(f"Error saving file: {e}")
        return None


st.title("Upload and Print PNG Image \n works best with 696 pixel wide image")

uploaded_file = st.file_uploader("Choose a PNG file to :printer:", type=['png'])

if uploaded_file is not None:
    file_path = save_uploaded_file(uploaded_file)
    if file_path:
        st.image(file_path, caption="Uploaded Image Preview")
        if st.button("Print", key="print_uploaded"):
            print_image(file_path)
            st.success("Image sent to printer!")

st.subheader("print one of Last 6 Label sent")

temp_dir = "temp"

@st.cache_data()
def load_images(images):
    loaded_images = []
    for image in images:
        image_path = os.path.join(temp_dir, image)
        img = Image.open(image_path)
        loaded_images.append((img, image))
    return loaded_images

# Check if the directory exists
if os.path.exists(temp_dir):
    files = os.listdir(temp_dir)
    # Filter only PNG files
    images = [file for file in files if file.endswith('.png')]
    # Reverse the list to get the last 6 images
    last_six_images = images[-6:][::-1]
    loaded_images = load_images(last_six_images)

    # Display each of the last 6 images
    for idx, (img, image) in enumerate(loaded_images):
        image_path = os.path.join(temp_dir, image)
        col1, col2 = st.columns(2)
        with col1:
            st.image(image_path)
        with col2:
            if st.button(f"Print {image}", key=f"print_{idx}"):
                print_image(image_path)
                st.success(f"Image {image} sent to printer!")

    # Display the rest of the images as a list (without preview)
    rest_of_images = images[:-6][::-1] # Excluding the last 6
    if rest_of_images:
        st.subheader("Rest of Labels:")
        for image in rest_of_images:
            if st.button(f"Print {image}", key=f"print_rest_{image}"):
                print_image(os.path.join(temp_dir, image))
                st.success(f"Image {image} sent to printer!")
else:
    st.error(f"The directory {temp_dir} does not exist.")

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