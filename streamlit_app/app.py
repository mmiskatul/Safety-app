import base64
import io
import json
import threading

import av
import requests
import socketio
import streamlit as st
from PIL import Image
from streamlit_webrtc import VideoProcessorBase, webrtc_streamer

st.set_page_config(page_title="PPE Safety MVP", layout="wide")

st.title("PPE Safety MVP")

with st.sidebar:
    st.header("Settings")
    api_url = st.text_input("API base URL", value="http://127.0.0.1:8000")
    st.caption("FastAPI should be running on this URL.")
    socket_url = st.text_input("Socket URL", value="http://127.0.0.1:8001")
    st.caption("Start the socket server for live detection.")

modes = [
    "Live Detection",
    "Camera Snapshot",
    "Image Upload",
    "Video Upload",
    "Incident Report",
    "Dashboard",
]
mode = st.selectbox("Mode", modes, index=0)


@st.cache_resource
def get_socket_client(url):
    sio = socketio.Client(reconnection=True, transports=["polling"])
    sio.connect(url, wait_timeout=5)
    return sio


@st.cache_resource
def get_socket_lock():
    return threading.Lock()


def post_file(endpoint, uploaded_file, data=None, timeout=120):
    files = {
        "file": (
            uploaded_file.name,
            uploaded_file.getvalue(),
            uploaded_file.type or "application/octet-stream",
        )
    }
    response = requests.post(f"{api_url}{endpoint}", files=files, data=data or {}, timeout=timeout)
    response.raise_for_status()
    return response.json()


def download_bytes(path, timeout=120):
    response = requests.get(f"{api_url}/download", params={"path": path}, timeout=timeout)
    response.raise_for_status()
    return response.content


def render_detection_results(result):
    summary = result.get("summary") or {}
    detections = result.get("detections") or []

    if summary:
        st.subheader("Summary")
        st.json(summary)

    if detections:
        st.subheader("Detections")
        st.dataframe(detections, use_container_width=True)


if mode == "Live Detection":
    st.subheader("Realtime camera detection")
    st.caption("Requires the socket server running on the Socket URL.")

    frame_skip = st.slider("Process every Nth frame", min_value=1, max_value=10, value=2)

    class LiveProcessor(VideoProcessorBase):
        def __init__(self, sio, lock, skip):
            self.sio = sio
            self.lock = lock
            self.skip = max(1, int(skip))
            self.counts = {}
            self._frame_index = 0

        def recv(self, frame):
            self._frame_index += 1
            if self._frame_index % self.skip != 0:
                return frame

            try:
                img = frame.to_image()
                buffer = io.BytesIO()
                img.save(buffer, format="JPEG", quality=80)
                payload = base64.b64encode(buffer.getvalue()).decode("utf-8")

                with self.lock:
                    result = self.sio.call("frame", payload, timeout=5)
            except Exception:
                return frame

            if isinstance(result, dict):
                self.counts = result.get("counts", {})
                encoded = result.get("frame")
                if encoded:
                    try:
                        decoded = base64.b64decode(encoded)
                        annotated = Image.open(io.BytesIO(decoded)).convert("RGB")
                        return av.VideoFrame.from_image(annotated)
                    except Exception:
                        return frame
            return frame

    try:
        sio = get_socket_client(socket_url)
        lock = get_socket_lock()
    except Exception as exc:
        st.error(f"Socket connection failed: {exc}")
        sio = None
        lock = None

    if sio and lock:
        ctx = webrtc_streamer(
            key="live-detect",
            video_processor_factory=lambda: LiveProcessor(sio, lock, frame_skip),
            media_stream_constraints={"video": True, "audio": False},
        )

        if ctx.video_processor:
            st.subheader("Latest counts")
            st.json(ctx.video_processor.counts or {})

elif mode == "Camera Snapshot":
    st.subheader("Capture a photo and run detection")
    photo = st.camera_input("Take a snapshot")
    if photo is not None:
        with st.spinner("Detecting..."):
            try:
                result = post_file("/detect/image", photo)
            except requests.RequestException as exc:
                st.error(f"Detection failed: {exc}")
            else:
                output_path = result.get("output_path")
                if output_path:
                    try:
                        img_bytes = download_bytes(output_path)
                        st.image(img_bytes, caption="Detected image", use_container_width=True)
                    except requests.RequestException as exc:
                        st.warning(f"Could not download result image: {exc}")
                render_detection_results(result)

elif mode == "Image Upload":
    st.subheader("Upload an image for detection")
    uploaded = st.file_uploader("Choose an image", type=["jpg", "jpeg", "png", "bmp"])
    if uploaded is not None and st.button("Detect Image"):
        with st.spinner("Detecting..."):
            try:
                result = post_file("/detect/image", uploaded)
            except requests.RequestException as exc:
                st.error(f"Upload failed: {exc}")
            else:
                output_path = result.get("output_path")
                if output_path:
                    try:
                        img_bytes = download_bytes(output_path)
                        st.image(img_bytes, caption="Detected image", use_container_width=True)
                    except requests.RequestException as exc:
                        st.warning(f"Could not download result image: {exc}")
                render_detection_results(result)

elif mode == "Video Upload":
    st.subheader("Upload a video for detection")
    uploaded = st.file_uploader("Choose a video", type=["mp4", "mov", "avi", "mkv"])
    if uploaded is not None and st.button("Detect Video"):
        with st.spinner("Processing video..."):
            try:
                result = post_file("/detect/video", uploaded, timeout=300)
            except requests.RequestException as exc:
                st.error(f"Upload failed: {exc}")
            else:
                output_path = result.get("output_path")
                if output_path:
                    try:
                        video_bytes = download_bytes(output_path, timeout=300)
                        st.video(video_bytes)
                    except requests.RequestException as exc:
                        st.warning(f"Could not download result video: {exc}")
                summary = result.get("summary")
                if summary:
                    st.subheader("Summary")
                    st.json(summary)

elif mode == "Incident Report":
    st.subheader("Create an incident report")
    uploaded = st.file_uploader("Choose an image", type=["jpg", "jpeg", "png", "bmp"])
    description = st.text_area("Incident description")
    if uploaded is not None and description.strip() and st.button("Generate Report"):
        with st.spinner("Generating report..."):
            try:
                result = post_file("/save_incident", uploaded, data={"description": description})
            except requests.RequestException as exc:
                st.error(f"Report generation failed: {exc}")
            else:
                pdf_path = result.get("pdf_path")
                if pdf_path:
                    try:
                        pdf_bytes = download_bytes(pdf_path)
                        st.success("Report generated.")
                        st.download_button(
                            "Download PDF",
                            data=pdf_bytes,
                            file_name="incident_report.pdf",
                            mime="application/pdf",
                        )
                    except requests.RequestException as exc:
                        st.warning(f"Could not download PDF: {exc}")

elif mode == "Dashboard":
    st.subheader("Metrics dashboard")
    if st.button("Refresh"):
        st.experimental_rerun()

    try:
        logs_bytes = download_bytes("app/output/logs.json")
        logs = json.loads(logs_bytes.decode("utf-8"))
    except requests.HTTPError:
        st.info("No logs found yet. Run detection or incident reporting first.")
        logs = []
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        st.error(f"Could not parse logs: {exc}")
        logs = []
    except requests.RequestException as exc:
        st.error(f"Failed to load logs: {exc}")
        logs = []

    if logs:
        prevention_count = sum(1 for log in logs if log.get("type") == "prevention")
        incident_count = sum(1 for log in logs if log.get("type") == "incident")
        st.metric("Total Prevention Photos", prevention_count)
        st.metric("Total Incidents", incident_count)
        st.dataframe(logs, use_container_width=True)
