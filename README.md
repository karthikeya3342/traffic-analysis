# 🚦 Intelligent Traffic Analysis System

A comprehensive computer vision solution for real-time traffic monitoring, queue analysis, and violation detection using YOLO and Streamlit.

![Traffic Analysis Dashboard](https://github.com/user-attachments/assets/placeholder-image) 
*(Note: Replace with actual screenshot)*

## ✨ Features

-   **Real-time Vehicle Counting**: DetectsCars, Buses, Trucks, and Motorcycles using YOLOv11/v8.
-   **Queue Analysis**:
    -   **Density Estimation**: Area-based calculation for accurate congestion reporting.
    -   **Lane-wise Monitoring**: Configurable ROIs for multiple lanes.
-   **Violation Detection**:
    -   **Red Light Violation**: Identifies vehicles crossing stop lines when signal is RED.
    -   **Rash Driving**: Detects aggressive driving behaviors.
-   **Interactive Dashboard**:
    -   Live Video Feed with Overlays.
    -   Real-time Metrics (Counters, Queue Status).
    -   **Post-Analysis Trends**: Dynamic graphs for Vehicle Volume and Queue Density per 30 frames.
    -   **Data Export**: Download detailed CSV logs and JSON summaries.
-   **Smart Configuration**:
    -   Draw lanes and stop lines directly in the UI.
    -   Auto-save and auto-load configurations.

## 🛠️ Installation

### Prerequisites
-   Python 3.8+
-   CUDA-enabled GPU (Recommended) or CPU
-   FFmpeg (for video re-encoding)

### Steps
1.  **Clone the Repository**:
    ```bash
    git clone https://github.com/karthikeya3342/traffic-analysis.git
    cd traffic-analysis
    ```

2.  **Install Dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

## 🚀 Usage

### 1. Run the Dashboard (Recommended)
The Streamlit dashboard is the primary interface for configuring lanes and running analysis.

```bash
python -m streamlit run app.py
```

### 2. Configure Lanes
1.  Open the dashboard in your browser (`http://localhost:8501`).
2.  Navigate to **"Configure Lanes"** in the sidebar.
3.  Draw **Polygons** for Lanes (Blue) and **Lines** for Stop Lines (Red).
4.  Click **"Save Configuration"**.

### 3. Run Analysis
1.  Go to **"Run Analysis"**.
2.  Select a video source (uploaded to `data/` folder).
3.  Click **"Run Analysis"**.
4.  Monitor live stats.
5.  Once finished, view the **Analysis Trends** graphs and download reports.

### 4. CLI Usage (Headless)
You can also run the core analysis script without the UI:
```bash
python main.py --source data/input_video.mp4 --output output/result.mp4
```

## ⚙️ Configuration

The system is highly configurable via `config/config.yaml`:

```yaml
detection:
  model: yolo11n.pt      # YOLO Model path
  confidence_threshold: 0.3
  classes: [2, 3, 5, 7]  # COCO Class IDs (Car, Bus, Truck...)

analytics:
  lanes: []              # Populated automatically by the UI
  speed_limit_pixels: 25
  queue_threshold_speed: 2

video:
  resize_width: 1280
  resize_height: 720
```

## 📂 Project Structure

```
traffic-analysis/
├── app.py                  # Streamlit Dashboard Entry Point
├── main.py                 # Core Analysis Pipeline
├── config/
│   └── config.yaml         # Configuration File
├── data/
│   ├── stats.csv           # Analysis Logs (Generated)
│   └── final_summary.json  # Run Summary (Generated)
├── src/
│   ├── analytics.py        # Logic for Violations/Queues
│   ├── detector.py         # YOLO Inference
│   ├── tracker.py          # Object Tracking (ByteTrack/SORT)
│   ├── visualizer.py       # Drawing Overlays
│   └── ui/                 # Dashboard Components
└── requirements.txt        # Python Dependencies
```

## 🤝 Contributing

Contributions are welcome! Please open an issue or submit a pull request.

## 📜 License

MIT License.
