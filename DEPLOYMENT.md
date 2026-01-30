# Deployment Guide

This system uses **Streamlit**, which makes deployment straightforward. However, since it relies on heavy Computer Vision (OpenCV/YOLO), choosing the right platform is critical for performance.

## Option 1: Streamlit Community Cloud (Recommended for Demos)
Best for sharing a permanent link.
*Note: Free tier CPU may stutter with high-res video processing.*

### Steps:
1.  **Push to GitHub**:
    Ensure your code is in a public GitHub repository. The `requirements.txt` file is already prepared.
2.  **Sign Up**:
    Go to [share.streamlit.io](https://share.streamlit.io) and sign in with GitHub.
3.  **Deploy**:
    *   Click **"New app"**.
    *   Select your repository, branch (`main`), and file (`app.py`).
    *   Click **"Deploy"**.
4.  **Secrets (Optional)**:
    If you add privacy features later, you can configure them in the dashboard settings.

---

## Option 2: Ngrok (Best for Hackathon / High Performance)
Best if you want to use YOUR powerful computer (GPU/CPU) but show it on a public URL. This gives the smoothest frame rate.

### Steps:
1.  **Install Ngrok**:
    Download from [ngrok.com](https://ngrok.com/download).
2.  **Run Your App Locally**:
    ```bash
    python -m streamlit run app.py
    ```
    (Note the local URL, usually `http://localhost:8501`)
3.  **Expose Port**:
    Open a new terminal and run:
    ```bash
    ngrok http 8501
    ```
4.  **Share URL**:
    Ngrok will provide a public link (e.g., `https://a1b2-c3d4.ngrok-free.app`). Send this to the judges!

---

## Option 3: Docker (Professional)
If you need to deploy on a cloud server (AWS/GCP/Azure).

1.  **Build Image**:
    (A `Dockerfile` would be needed based on `python:3.9-slim` + `libgl1` dependencies).
2.  **Run Container**:
    ```bash
    docker build -t traffic-app .
    docker run -p 8501:8501 traffic-app
    ```

### Recommendation
For a hackathon presentation: **Use Option 2 (Ngrok)**. It leverages your local hardware speed while giving judges a live link.
