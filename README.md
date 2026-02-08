# PPE Safety MVP

This project runs a FastAPI backend with a Streamlit frontend.

## Run the backend

From the project root:

```powershell
cd backend
python -m uvicorn app.main:app --reload
```

Optional realtime socket server (not used by Streamlit):

```powershell
cd backend
python app/socket_server.py
```

## Run the Streamlit frontend

From the project root:

```powershell
pip install -r streamlit_app/requirements.txt
streamlit run streamlit_app/app.py
```

The Streamlit app expects the FastAPI backend at `http://127.0.0.1:8000`. You can change it in the sidebar.
