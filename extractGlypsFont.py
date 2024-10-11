import streamlit as st
from PIL import Image

# Streamlit app
st.title("Glyph Font Display")

# Load default font image
default_image_path = 'fonts/7x4_font.png'
font_image = Image.open(default_image_path)

# Create two columns for side-by-side display
col1, col2 = st.columns(2)

# Preview the default font image at 4x size without smoothing in the first column
with col1:
    font_image_resized = font_image.resize((font_image.width * 4, font_image.height * 4), Image.Resampling.NEAREST)
    st.image(font_image_resized, caption=default_image_path, use_column_width=False)

# Upload font image in the second column
with col2:
    uploaded_file = st.file_uploader("Upload Font Image", type=["png", "jpg", "jpeg"],label_visibility="collapsed")
    if uploaded_file is not None:
        font_image = Image.open(uploaded_file)

char_map = st.text_input("Character Map", value="ABCDEFGHIJKLMNOPQRSTUVWXYZ .,!?:;\"'$€+/0123456789")
# Input settings for width and height of glyphs
# Create four columns for side-by-side input
col1, col2, col3, col4 = st.columns(4)

with col1:
    glyph_width_corrected = st.number_input("Glyph Width", min_value=1, value=4)

with col2:
    glyph_height_corrected = st.number_input("Glyph Height", min_value=1, value=7)

with col3:
    grid_cols = st.number_input("Grid Columns", min_value=1, value=10)

with col4:
    grid_rows = st.number_input("Grid Rows", min_value=1, value=5)

glyph_width_adjusted = glyph_width_corrected + 1  # Adding 1 pixel for spacing on the right
glyph_height_adjusted = glyph_height_corrected + 1  # Adding 1 pixel for spacing on the bottom
glyphs_adjusted = []
for row in range(grid_rows):
    for col in range(grid_cols):
        left = col * glyph_width_adjusted
        upper = row * glyph_height_adjusted
        right = left + glyph_width_corrected  # Don't include the spacing pixel itself in the glyph
        lower = upper + glyph_height_corrected  # Don't include the spacing pixel itself in the glyph
        glyph = font_image.crop((left, upper, right, lower))
        glyphs_adjusted.append(glyph)

# Create a dictionary mapping characters to their corresponding glyphs
glyph_dict_adjusted = dict(zip(char_map, glyphs_adjusted))

# Function to display a sequence of glyphs together with one pixel distance between them
def display_text_together(text):
    # Calculate the width and height of the final image
    total_width = len(text) * (glyph_width_corrected + 1) - 1
    total_height = glyph_height_corrected

    # Create a new blank image
    final_image = Image.new('L', (total_width, total_height), color=255)

    # Paste each glyph onto the final image
    x_offset = 0
    for char in text:
        if char in glyph_dict_adjusted:
            glyph = glyph_dict_adjusted[char]
            final_image.paste(glyph, (x_offset, 0))
            x_offset += glyph_width_corrected + 1

    # Resize the final image for better visibility
    final_image_resized = final_image.resize((final_image.width * 5, final_image.height * 5), Image.Resampling.NEAREST)

    # Display the final image
    st.image(final_image_resized, caption="Sample Text", use_column_width=True)

# Input sample text
sample_text = st.text_input("Sample Text", value="HELLO WORLD").upper()

# Display the sample text
display_text_together(sample_text)