from brother_ql.raster import BrotherQLRaster
from brother_ql.conversion import convert
from brother_ql.backends.helpers import send
import usb.core

def process_print_job(image, printer_info, temp_file_path, rotate=0, dither=False, label_type="62"):
    """
    Process a single print job.
    Returns (success, error_message)
    """
    try:
        # Prepare the image for printing
        qlr = BrotherQLRaster(printer_info["model"])
        instructions = convert(
            qlr=qlr,
            images=[temp_file_path],
            label=label_type,
            rotate=rotate,
            threshold=70,  # Default CLI threshold
            dither=dither,
            compress=True,  # CLI uses compression by default
            red=False,
            dpi_600=False,
            hq=False,  # CLI doesn't use HQ by default
            cut=True,
        )

        # Debug logging
        print(f"""
        Print parameters:
        - Label type: {label_type}
        - Rotate: {rotate}
        - Dither: {dither}
        - Model: {printer_info['model']}
        - Backend: {printer_info['backend']}
        - Identifier: {printer_info['identifier']}
        """)

        # Try to print using Python API
        success = send(
            instructions=instructions,
            printer_identifier=printer_info["identifier"],
            backend_identifier="pyusb",
        )
        
        if not success:
            return False, "Failed to print using Python API"

        return True, None

    except usb.core.USBError as e:
        if "timeout error" in str(e):
            print("USB timeout error occurred, but it's okay.")
            return True, None
        error_msg = f"USBError encountered: {e}"
        print(error_msg)
        return False, error_msg

    except Exception as e:
        error_msg = f"Unexpected error during printing: {str(e)}"
        print(error_msg)
        return False, error_msg 