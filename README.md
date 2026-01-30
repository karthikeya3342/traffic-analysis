# Intelligent Traffic Analysis & Violation Detection System

## Overview
A computer vision system for traffic analytics, including vehicle counting, queue length estimation, and violation detection (red-light jumping, rash driving).

## Setup
1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. Place video in `data/`.
3. Update `config/config.yaml` with ROI coordinates.

## Usage
- Run analysis:
  ```bash
  python main.py
  ```
- Run dashboard:
  ```bash
  streamlit run app.py
  ```
