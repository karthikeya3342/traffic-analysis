import streamlit.elements.image

def apply_streamlit_patch():
    # --- Compatibility Patch for Streamlit < 1.39 vs Newer ---
    # Streamlit moved image_to_url to streamlit.elements.lib.image_utils
    # streamlit-drawable-canvas relies on the old location.
    if not hasattr(streamlit.elements.image, 'image_to_url'):
        try:
            from streamlit.elements.lib.image_utils import image_to_url
            streamlit.elements.image.image_to_url = image_to_url
        except ImportError:
            pass 
