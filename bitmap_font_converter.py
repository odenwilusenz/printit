#test for bitmap font converter and tester
# 7x4 font font by Johan Brodd 
# https://opengameart.org/sites/default/files/7x4%20font.png
# https://opengameart.org/content/7x4-font

import streamlit as st
import numpy as np
from PIL import Image
import pickle

def render_text(text, char_to_image, glyph_width, glyph_height):
    text_length = len(text)
    canvas_width = text_length * glyph_width
    canvas_height = glyph_height
    canvas = np.zeros((canvas_height, canvas_width), dtype=np.uint8)
    for i, char in enumerate(text):
        if char in char_to_image:
            x_start = i * glyph_width
            x_end = x_start + glyph_width
            canvas[:, x_start:x_end] = char_to_image[char]
    return canvas

st.title("Bitmap Font to Dictionary Converter & Tester")
fixed_char_set = "abcdefghij\nklmnopqrst\nuvwxyz .,!\n?:;\"'$£Üẍ©\n0123456789"
font_image = st.file_uploader("Upload your bitmap font image (.png, .jpg):", type=["png", "jpg"])
char_set = st.text_area("Enter your character set:", "'''" + fixed_char_set + "'''")

if font_image and char_set:
    font_image = Image.open(font_image).convert("L")
    image_width, image_height = font_image.size
    glyph_width = image_width // 10
    glyph_height = image_height // 5
    char_set = char_set.strip().replace("\\\\n", "").replace("\\n", "")
    char_list = list(char_set)
    font_array = np.array(font_image)
    char_to_image = {}

    resize_option = st.checkbox("Resize glyphs?")
    new_width = 0
    if resize_option:
        new_width = st.slider("New width:", min_value=1, max_value=50, value=glyph_width)
        scale_factor = new_width / glyph_width

    spacer=1 #theres a 1 pixel between them glyphs
    for i in range(5):
        for j in range(10):
            x_start, y_start = j * glyph_width, i * glyph_height
            x_end, y_end = (x_start + glyph_width)-spacer, (y_start + glyph_height)-spacer
            glyph_image = Image.fromarray(font_array[y_start:y_end, x_start:x_end], 'L')
            if resize_option:
                new_height = int(glyph_height * scale_factor)
                glyph_image = glyph_image.resize((new_width, new_height), Image.NEAREST)
            char_to_image[char_list.pop(0)] = np.array(glyph_image)

    st.subheader("Preview of the first 5 glyphs:")
    for char, img in list(char_to_image.items())[:5]:
        st.image(img, caption=f"Glyph: '{char}'", channels="GRAY")

    pickle.dump(char_to_image, open("char_to_image.pkl", "wb"))
    st.download_button("Download Character to Image Dictionary", "char_to_image.pkl", "char_to_image.pkl")

    test_text = st.text_input("Test text rendering:")

    if test_text:
        rendered_image = render_text(test_text, char_to_image, new_width if resize_option else glyph_width, new_height if resize_option else glyph_height)
        st.image(rendered_image, caption="Rendered Text", channels="GRAY")
