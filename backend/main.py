from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import os
import shutil
import uuid
from typing import Optional
import math
import numpy as np
import pandas as pd
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
def _sanitize(obj):
    # Recursively convert objects to JSON-safe Python types, replacing NaN/inf with None
    if obj is None:
        return None
    if isinstance(obj, dict):
        return {k: _sanitize(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_sanitize(v) for v in obj]
    # numpy scalar
    if isinstance(obj, (np.generic,)):
        try:
            return _sanitize(obj.item())
        except Exception:
            return str(obj)
    # floats: check NaN/inf
    if isinstance(obj, float):
        if math.isnan(obj) or math.isinf(obj):
            return None
        return obj
    return obj
app = FastAPI()

plots_dir = os.path.join(os.path.dirname(__file__), 'plots')
os.makedirs(plots_dir, exist_ok=True)
app.mount("/plots", StaticFiles(directory=plots_dir), name="plots")

# Allow requests from the frontend dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'uploads')
os.makedirs(UPLOAD_DIR, exist_ok=True)

@app.get("/")
def serve_react_app():
    if os.path.exists(os.path.join(frontend_build_dir, "index.html")):
        return FileResponse(os.path.join(frontend_build_dir, "index.html"))
    return {"message": "API is running. Frontend build not found."}


def _resolve_path(file_id: str) -> str:
    path = os.path.join(UPLOAD_DIR, file_id)
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="File not found")
    return path


@app.post('/upload')
async def upload(file: UploadFile = File(...)):
    ext = os.path.splitext(file.filename)[1]
    file_id = f"{uuid.uuid4().hex}{ext}"
    dest = os.path.join(UPLOAD_DIR, file_id)
    try:
        with open(dest, 'wb') as f:
            shutil.copyfileobj(file.file, f)
    finally:
        file.file.close()
    return {"file_id": file_id, "filename": file.filename}


@app.get('/columns/{file_id}')
def columns(file_id: str):
    try:
        from pipeline.eda import read_dataset
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    path = _resolve_path(file_id)
    df = read_dataset(path)
    cols = list(df.columns)
    preview = df.head(5).to_dict(orient='records')
    dtypes = {c: str(t) for c, t in df.dtypes.items()}
    nulls = df.isnull().sum().to_dict()
    return {"columns": cols, "preview": preview, "dtypes": dtypes, "nulls": nulls}


@app.get('/eda/{file_id}')
def eda(file_id: str):
    try:
        from pipeline.eda import read_dataset
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    path = _resolve_path(file_id)
    df = read_dataset(path)
    describe = df.describe(include='all').to_dict()
    preview = df.head(5).to_dict(orient='records')
    info = {
        'shape': df.shape,
        'dtypes': df.dtypes.astype(str).to_dict(),
        'nulls': df.isnull().sum().to_dict(),
        'describe': _sanitize(describe),
        'preview': _sanitize(preview)
    }
    return info


@app.post('/clean/{file_id}')
def clean_data(file_id: str):
    try:
        from pipeline.eda import read_dataset
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
    path = _resolve_path(file_id)
    try:
        df = read_dataset(path)
        initial_rows = len(df)
        df.drop_duplicates(inplace=True)
        
        # Basic imputation
        numeric_cols = df.select_dtypes(include=['number']).columns
        for col in numeric_cols:
            if df[col].isnull().any():
                df[col].fillna(df[col].median(), inplace=True)
                
        cat_cols = df.select_dtypes(include=['object', 'category']).columns
        for col in cat_cols:
            if df[col].isnull().any() and not df[col].mode().empty:
                df[col].fillna(df[col].mode()[0], inplace=True)
        
        final_rows = len(df)
        
        # Always save as CSV. If parquet, this overwrites but frontend assumes file_id doesn't change extension.
        df.to_csv(path, index=False)
        
        return {
            "status": "Success",
            "message": f"Dataset cleaned. Removed {initial_rows - final_rows} duplicate rows. Imputed missing values with Median/Mode.",
            "rowsAfter": str(final_rows)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post('/drop-columns/{file_id}')
def drop_columns(file_id: str, columns: str = Form(...)):
    try:
        from pipeline.eda import read_dataset
        path = _resolve_path(file_id)
        df = read_dataset(path)
        
        cols_to_drop = [c.strip() for c in columns.split(',') if c.strip()]
        if not cols_to_drop:
            raise ValueError("No columns provided to drop.")
            
        df.drop(columns=cols_to_drop, inplace=True, errors='ignore')
        df.to_csv(path, index=False)
        
        return {
            "status": "Success", 
            "message": f"Dropped columns: {', '.join(cols_to_drop)}",
            "remaining_columns": list(df.columns)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get('/download/{file_id}')
def download_data(file_id: str):
    path = _resolve_path(file_id)
    filename = f"cleaned_{file_id}"
    if not filename.endswith('.csv'):
        filename += '.csv'
    return FileResponse(path, filename=filename, media_type='text/csv')

@app.post('/visualize/{file_id}')
def get_visualizations(file_id: str):
    try:
        from pipeline.eda import generate_plots
        path = _resolve_path(file_id)
        
        plot_dir = os.path.join(plots_dir, file_id)
        os.makedirs(plot_dir, exist_ok=True)
        
        saved_files = generate_plots(path, out_dir=plot_dir)
        plot_urls = [f"http://localhost:8000/plots/{file_id}/{os.path.basename(f)}" for f in saved_files]
        
        return {"plots": plot_urls}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post('/visualize-custom/{file_id}')
def visualize_custom(file_id: str, col1: str = Form(...), plot_type: str = Form(...), col2: Optional[str] = Form(None)):
    try:
        from pipeline.eda import generate_single_plot
        path = _resolve_path(file_id)
        
        plot_dir = os.path.join(plots_dir, file_id)
        os.makedirs(plot_dir, exist_ok=True)
        
        saved_file = generate_single_plot(path, plot_type, col1, col2, out_dir=plot_dir)
        if saved_file:
            plot_url = f"http://localhost:8000/plots/{file_id}/{os.path.basename(saved_file)}"
            return {"plot": plot_url}
        else:
            raise HTTPException(status_code=400, detail="Invalid plot configuration or generation failed.")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post('/train/{file_id}')
def train_endpoint(file_id: str, target: str = Form(...), model_type: str = Form('auto')):
    try:
        from pipeline.train import train as train_fn
        from pipeline.train import read_dataset
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    path = _resolve_path(file_id)
    try:
        res = train_fn(path, target, model_type=model_type)
    except SystemExit as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    return res


@app.post('/hypothesis/{file_id}')
def hypothesis_endpoint(file_id: str, column: str = Form(...), test: str = Form('ttest'), group_column: Optional[str] = Form(None)):
    try:
        from pipeline.hypothesis import hypothesis as hyp_fn
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    path = _resolve_path(file_id)
    try:
        res = hyp_fn(path, column, test=test, group_column=group_column)
    except SystemExit as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    return res


# Chat/LLM endpoint removed — backend only exposes dataset/eda/train/hypothesis endpoints

# Mount frontend build directory specifically over / to serve index.html
from starlette.responses import FileResponse
frontend_build_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'frontend', 'build')

# Mount the frontend React static files over /static
frontend_static_dir = os.path.join(frontend_build_dir, 'static')
if os.path.exists(frontend_static_dir):
    app.mount("/static", StaticFiles(directory=frontend_static_dir), name="frontend_static")

@app.get("/{full_path:path}")
def serve_react_app(full_path: str):
    index_path = os.path.join(frontend_build_dir, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path, headers={"Cache-Control": "no-cache, no-store, must-revalidate"})
    return {"message": "API is running. Frontend build not found."}

if __name__ == '__main__':
    import uvicorn
    # Use environment variable PORT if present, otherwise 8000
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run('backend.main:app', host='0.0.0.0', port=port, reload=True)
