import streamlit as st
from PIL import Image, ImageDraw, ImageFont
import slugify
import requests
import io, base64, os, re
import subprocess
import tempfile
import hashlib
from datetime import datetime
import time
import txt2img_util

# Access the current query parameters
query_params = st.experimental_get_query_params()

# Check if the 'copies' parameter exists
# add to url "?copies=25"
copies = int(query_params.get("copies", [1])[0])  # Default to 1 copy if not specified


# Function to list the last 15 saved images, excluding those ending with "dithered"
def list_saved_images(directories=["temp", "labels"]):
    files = []
    for directory in directories:
        if os.path.exists(directory):
            files.extend([
                os.path.join(directory, file) for file in os.listdir(directory)
                if not file.endswith("dithered.png") and not file.endswith("dithered.jpg") and not file.endswith("dithered.gif") 
                and file.endswith(('.png', '.jpg', '.gif'))
            ])

    # Sort files by modification time in descending order
    files.sort(key=lambda x: os.path.getmtime(x), reverse=True)

    # Return the last 15 files
    return files[:15]



# Function to find .ttf fonts
def find_fonts():
    font_dirs = ["fonts", "/usr/share/fonts/"]
    fonts = []
    for dir in font_dirs:
        if os.path.exists(dir):
            for root, _, files in os.walk(dir):
                for file in files:
                    if file.endswith(".ttf"):
                        fonts.append(os.path.join(root, file))
    return fonts


def safe_filename(text):
    # Sanitize the text to remove illegal characters and replace spaces with underscores
    sanitized_text = re.sub(r'[<>:"/\\|?*\n\r]+', '', text).replace(' ', '_')

    # Get the current time in epoch format
    epoch_time = int(time.time())

    # Return the filename
    # return f"{sanitized_text}_{epoch_time}.png"
    return f"{sanitized_text}.png"


# Ensure label directory exists
label_dir = "labels"
os.makedirs(label_dir, exist_ok=True)


def generate_image(prompt, steps):
    txt2img = txt2img_util.txt2img()
    return txt2img.generate(prompt)
    # payload = {
    #     "prompt": prompt,
    #     "steps": 16,
    #     "width": 696
    # }
    
    # response = requests.post(url=f'https://y7bbzpsxx1vt.share.zrok.io/sdapi/v1/txt2img', json=payload)
    # r = response.json()
    
    # for i in r['images']:
    #     image = Image.open(io.BytesIO(base64.b64decode(i.split(",",1)[0])))
    #     return image
    
def add_white_background_and_convert_to_grayscale(image):
    # Check if the image has transparency (an alpha channel)
    if image.mode == 'RGBA':
        # Create a white background of the same size as the original image
        white_background = Image.new('RGBA', image.size, 'white')
        # Paste the original image onto the white background
        white_background.paste(image, mask=image.split()[3]) # Using the alpha channel as the mask
        image = white_background

    # Convert the image to grayscale
    return image.convert('L')

def rotate_image(image, angle):
    return image.rotate(angle, expand=True)

def resize_and_dither(image):
    # Resize the image to 696 width while maintaining the aspect ratio
    new_width = 696
    aspect_ratio = image.width / image.height
    new_height = int(new_width / aspect_ratio)
    resized_image = image.resize((new_width, new_height), Image.LANCZOS)

    # Convert the resized image to grayscale
    resized_grayscale_image = resized_image.convert("L")

    # Apply Floyd-Steinberg dithering
    dithered_image = resized_grayscale_image.convert("1", dither=Image.FLOYDSTEINBERG)
    
    return resized_grayscale_image, dithered_image

def print_image(image):
    # Save the image to a temporary file
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as temp_file:
        temp_file_path = temp_file.name
        image.save(temp_file_path, "PNG")
        
    # Construct the print command
    printer_ql750="0x2028"
    printer_id1="000M6Z401370"

    printer_QL550b="0x2016"
    printer_ql500a="0x2015"
    printer_id2="000M6Z401370"
    

    command = f"brother_ql -b pyusb --model QL-570 -p usb://0x04f9:{printer_ql750}/{printer_id1} print -l 62 \"{temp_file_path}\""
    #good
    # command = f"brother_ql -b pyusb --model QL-500 -p usb://0x04f9:{printer_ql500a}/{printer_id2} print -l 62 \"{temp_file_path}\""
    #badblink
    # command = f"brother_ql -b pyusb --model QL-550 -p usb://0x04f9:{printer_QL550b} print -l 62 \"{temp_file_path}\""
    
    print(command)
    # Run the print command
    for _ in range(copies):
        # st.balloons()
        subprocess.run(command, shell=True)

def find_url(string):
    url_pattern = re.compile(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+')
    urls = re.findall(url_pattern, string)
    return urls

def img_concat_v(im1, im2):
    image_width=696
    dst = Image.new('RGB', (im1.width, im1.height + image_width))
    dst.paste(im1, (0, 0))
    im2 = im2.resize((image_width, image_width))

    dst.paste(im2, (0, im1.height))
    return dst




# Streamlit app
st.title('STICKER FACTORY @ [TAMI](https://telavivmakers.org)')

st.subheader(":printer: hard copies of images and text")


tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs(["Sticker", "Label", "Text2image", "Webcam","Cat" ,"history", "FAQ"])

#sticker
with tab1:
    st.subheader("Sticker")

    # Allow the user to upload an image
    uploaded_image = st.file_uploader("Choose an image file to print", type=['png', 'jpg', 'gif', 'webp'])

    # Initialize a variable for the image to be processed
    image_to_process = None

    # Check if an image has been uploaded
    if uploaded_image is not None:
        image_to_process = Image.open(uploaded_image).convert('RGB')

    # Alternatively, check if an image has been selected from the gallery
    elif 'selected_image_path' in st.session_state:
        image_to_process = Image.open(st.session_state['selected_image_path'])

    # If an image is ready to be processed (either uploaded or selected from the gallery)
    if image_to_process is not None:
        # Get the original filename without extension
        # For gallery images, you might need a different approach to get a meaningful filename
        original_filename_without_extension = os.path.splitext(uploaded_image.name)[0] if uploaded_image else "selected_image"

        grayimage = add_white_background_and_convert_to_grayscale(image_to_process)
        resized_image, dithered_image = resize_and_dither(grayimage)
        
        st.image(image_to_process, caption="Original Image")
        st.image(dithered_image, caption="Resized and Dithered Image")

        # Paths to save the original and dithered images in the 'temp' directory with postfix
        original_image_path = os.path.join('temp', original_filename_without_extension + '_original.png')
        dithered_image_path = os.path.join('temp', original_filename_without_extension + '_dithered.png')

        # Save both original and dithered images
        image_to_process.save(original_image_path, "PNG")
        dithered_image.save(dithered_image_path, "PNG")

        # print options
        colc, cold = st.columns(2)
        with colc:
            if st.button('Print Original Image'):
                print_image(image_to_process)
                st.success('Original image sent to printer!')
        with cold:
            if st.button('Print Dithered Image'):
                print_image(dithered_image)
                st.success('Dithered image sent to printer!')

        cole, colf = st.columns(2)
        with cole:
            if st.button('Print Original+rotated Image'):
                rotated_org_image = rotate_image(image_to_process, 90)
                print_image(rotated_org_image)
                st.success('Original+rotated image sent to printer!')

        with colf:
            if st.button('Print dithered+rotated Image'):
                rotated_image = rotate_image(dithered_image, 90)
                print_image(rotated_image)
                st.success('Dithered+rotated image sent to printer!')



#label
with tab2:
    st.subheader(":printer: a label")

    img = ""

    # Function to calculate the actual image height based on the bounding boxes of each line
    def calculate_actual_image_height_with_empty_lines(text, font, line_spacing=10):
        draw = ImageDraw.Draw(Image.new("RGB", (1, 1), color="white"))  # Dummy image for calculation
        total_height = 0
        for line in text.split('\n'):
            if line.strip():  # Non-empty lines
                bbox = draw.textbbox((0, 0), line, font=font)
                text_height = bbox[3] - bbox[1]
            else:  # Empty lines
                text_height = font.getbbox("x")[3] - font.getbbox("x")[1]  # Use the height of 'x' as the height for empty lines
            total_height += text_height + line_spacing  # Add line spacing
        return total_height - line_spacing  # Remove the last line spacing

    # Function to calculate the maximum font size based on the width of the longest line
    def calculate_max_font_size(width, text, font_path, start_size=10, end_size=200, step=1):
        draw = ImageDraw.Draw(Image.new("RGB", (1, 1), color="white"))  # Dummy image for calculation
        max_font_size = start_size

        for size in range(start_size, end_size, step):
            font = ImageFont.truetype(font_path, size)
            adjusted_lines = []
            for line in text.split('\n'):
                adjusted_lines.append(line)

            max_text_width = max([draw.textbbox((0, 0), line, font=font)[2] for line in adjusted_lines if line.strip()])
            
            if max_text_width <= width:
                max_font_size = size
            else:
                break

        return max_font_size


    # Multiline Text Input
    text = st.text_area("Enter your text to print","write something", height=200)
    # Check if the text has been changed by the user
    if text:                                                                                                                                           
        urls = find_url(text)
        if urls:
            st.success("Found URLs: we might automate the QR code TODO")                                                                                                                        
            for url in urls:
                st.write(url)  

        # init some font vars
        available_fonts = find_fonts()
        font=available_fonts[0]
        alignment = "center"
        fnt = ImageFont.truetype(font, 20) # Initialize Font
        max_size = calculate_max_font_size(696, text, font) 
        font_size = max_size
        
        fontstuff = st.checkbox("font settings", value=False)
        col1, col2 = st.columns(2)
        if fontstuff:
            # Font Selection
            with col1:
                font = st.selectbox("Choose your font", available_fonts)

            # Alignment
            with col2:
                alignment_options = ["left", "center", "right"]
                alignment = st.selectbox("Choose text alignment", alignment_options, index=1)
            font_size = st.slider("Font Size", 5, max_size+5, max_size)
            font_size
        # Font Size
        fnt = ImageFont.truetype(font, font_size) # Initialize Font
        line_spacing = 20  # Adjust this value to set the desired line spacing

        # Calculate the new image height based on the bounding boxes
        new_image_height = calculate_actual_image_height_with_empty_lines(text, fnt, line_spacing)

        # Create Image
        y = 5  # Start from
        img = Image.new("RGB", (696, new_image_height+10), color="white")
        d = ImageDraw.Draw(img)

        # Draw Text
        for line in text.split('\n'):
            text_width = 0  # Initialize to zero

            if line.strip():  # For non-empty lines
                bbox = d.textbbox((0, y), line, font=fnt)
                text_width = bbox[2] - bbox[0]
                text_height = bbox[3] - bbox[1]
            else:  # For empty lines
                text_height = fnt.getbbox("x ")[3] - fnt.getbbox("x")[1]  # Use the height of an x as the height for empty lines

            if alignment == "center":
                x = (696 - text_width) // 2
            elif alignment == "right":
                x = 696 - text_width
            else:
                x = 0

            d.text((x, y), line, font=fnt, fill=(0, 0, 0))
            y += text_height + line_spacing  # Move down based on text height and line spacing
        
        # Save the label image
        if text != "write something":
            filename = safe_filename(text)
            file_path = os.path.join(label_dir, filename)
            img.save(file_path, "PNG")
            st.success(f"Label saved as {filename}")
        




    # QR code


    import qrcode
    qr = qrcode.QRCode(
        border=0
    )

    qrurl = st.text_input("add a QRcode to your sticker",)
    if qrurl:
        #we have text generate qr
        qr.add_data(qrurl)
        qr.make(fit=True)
        imgqr = qr.make_image(fill_color="black", back_color="white")

        #save to image
        # add random 4 letetrs to file name
        # letters = string.ascii_lowercase
        # random_string = ''.join(random.choice(letters) for i in range(4))
        # qrimgpath = os.path.join('temp', "qr_" + random_string + '.png')
        # imgqr.save(qrimgpath, "PNG")

        if imgqr and img:
            #add qr below the label
            imgqr = img_concat_v(img, imgqr)
            st.image(imgqr, use_column_width=True)
            if st.button('Print sticker+qr'):
                    print_image(imgqr)
        elif imgqr and not(img):
            # st.image(imgqr, use_column_width=True)
            if st.button('Print sticker'):
                    print_image(imgqr)


    if text and not(qrurl):
        st.image(img, use_column_width=True)
        if st.button('Print sticker'):
                print_image(img)  # Needs definition
                st.success('sticker sent to printer')
    st.markdown('''
                * label will automaticly resize to fit the longest line, so use linebreaks.   
                * on pc `ctrl+enter` will submit, on mobile click outside the `text_area` to process.
                ''')


#text2img
# Streamlit reruns the script every time the user interacts with the page. 
# To execute code only when a new prompt is entered, you need to keep track of the last prompt value
if 'last_prompt' not in st.session_state:
    st.session_state.last_prompt = None

with tab3:
    st.subheader(":printer: image from text")
    st.write("using tami stable diffusion bot")
    prompt = st.text_input("Enter a prompt")
    if prompt:
        print("generating image from prompt: " + prompt)
        generatedImage = generate_image(prompt, 20)
        resized_image, dithered_image = resize_and_dither(generatedImage)
        col1, col2 = st.columns(2)
        with col1:
            st.image(resized_image, caption="Original Image")
        with col2:
            st.image(dithered_image, caption="Resized and Dithered Image")
        slugprompt = slugify.slugify(prompt)
        original_image_path = os.path.join('temp', "txt2img_" + slugprompt + '.png')
        generatedImage.save(original_image_path, "PNG")         #save image
        
        
        col3, col4 = st.columns(2)
        with col3:
            if st.button('Print Original Image'):
                print_image(resized_image)
                st.success('Original image sent to printer!')
        with col4:
            if st.button('Print Dithered Image'):
                print_image(dithered_image)
                st.success('Dithered image sent to printer!')
        # print_image(dithered_image)
        
        # Update last prompt
        st.session_state.last_prompt = prompt

# webcam
with tab4:
    st.subheader(":printer: a snapshot")
    on = st.toggle('ask user for camera permission')
    if on:
        picture = st.camera_input("Take a picture")
        if picture is not None:
            picture = Image.open(picture).convert('RGB')
            # Get the original filename without extension
            grayimage = add_white_background_and_convert_to_grayscale(picture)
            resized_image, dithered_image = resize_and_dither(grayimage)
            
            st.image(dithered_image, caption="Resized and Dithered Image")

            # print options
            colc, cold = st.columns(2)
            with colc:
                if st.button('Print rotated Image'):
                    rotated_image = rotate_image(dithered_image, 90)
                    print_image(rotated_image)
                    st.balloons()
                    st.success('rotated image sent to printer!')
            with cold:
                if st.button('Print Image'):
                    print_image(dithered_image)
                    st.success('image sent to printer!')

# cat

with tab5:
    st.subheader(":printer: a cat")
    st.caption("from the fine folks at https://thecatapi.com/")
    if st.button("Fetch cat"):
        # Fetch API key from Streamlit secrets
        api_key = st.secrets["cat_api_key"]
        caturl = "https://api.thecatapi.com/v1/images/search"

        # Fetch JSON data
        api_url = f"{caturl}?limit=1&type=static&api_key={api_key}"
        response = requests.get(api_url)
        data = response.json()

        # Extract image URL from JSON
        image_url = data[0]['url']
        
        # Fetch the image
        image_response = requests.get(image_url)
        img = Image.open(io.BytesIO(image_response.content))        
        # Display the image
        grayimage = add_white_background_and_convert_to_grayscale(img)
        resized_image, dithered_image = resize_and_dither(grayimage)
        st.image(img, caption="Fetched Cat Image")
        # Your print logic here
        print_image(dithered_image)

#histroy
with tab6:
    st.subheader("Gallery of Last 15 Labels and Stickers")
    saved_images = list_saved_images()
    
    for i, image_path in enumerate(saved_images):
        cols = st.columns([1, 3])
        with cols[0]:
            if st.button(f"Select #{i}", key=f"btn_{i}"):  # Unique key for each button
                st.session_state['selected_image_path'] = image_path
                st.success('image selected, goto **Sticker** tab for further processing and printing')

        with cols[1]:
            image = Image.open(image_path)
            st.image(image, use_column_width=True)
                
# faq
with tab7:
    st.subheader("FAQ:")
    st.markdown(
        '''
        *dithering* is suggested (sometimes inforced) if source is not lineart as grayscale and color look bad at thermal printer  
        
        all uploaded images and generated labels are saved  
        uploaded camera snapshot are NOT saved, only printed. 

        app [code](https://github.com/5shekel/printit)
        
        PRINT ALOT is the best!
        '''
        )
    st.image(Image.open('assets/station_sm.jpg'), caption="TAMI printshop")