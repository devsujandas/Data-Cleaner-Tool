from fastapi import FastAPI, APIRouter, UploadFile, File, HTTPException, Form
from fastapi.responses import FileResponse, Response
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional, Union
import uuid
from datetime import datetime
import pandas as pd
import numpy as np
import json
import io
import tempfile
import base64

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Create the main app without a prefix
app = FastAPI(title="Data Cleaner API", version="1.0.0")

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# Data Models
class FileInfo(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    filename: str
    file_type: str
    size: int
    upload_timestamp: datetime = Field(default_factory=datetime.utcnow)

class CleaningOptions(BaseModel):
    remove_duplicates: bool = False
    handle_missing: str = "none"  # "drop", "fill", "none"
    fill_value: Optional[Union[str, int, float]] = None
    column_renames: Dict[str, str] = {}
    find_replace: Dict[str, Dict[str, str]] = {}  # {column: {old: new}}
    trim_whitespace: bool = False
    data_type_conversions: Dict[str, str] = {}  # {column: type}
    merge_files: List[str] = []

class DataStatistics(BaseModel):
    rows: int
    columns: int
    missing_values: Dict[str, int]
    data_types: Dict[str, str]
    unique_values: Dict[str, int]
    numeric_stats: Dict[str, Dict[str, float]]

# File storage (in production, use cloud storage)
UPLOAD_DIR = ROOT_DIR / "tmp" / "data_cleaner_uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# Utility functions
def read_file_to_dataframe(file_path: str, file_type: str) -> pd.DataFrame:
    """Read different file formats into pandas DataFrame"""
    if file_type == "csv":
        return pd.read_csv(file_path)
    elif file_type == "xlsx":
        return pd.read_excel(file_path)
    elif file_type == "json":
        return pd.read_json(file_path)
    else:
        raise HTTPException(status_code=400, detail=f"Unsupported file type: {file_type}")

def calculate_statistics(df: pd.DataFrame) -> DataStatistics:
    """Calculate comprehensive statistics for the DataFrame"""
    # Convert any NaN values to proper handling
    missing_values = {}
    for col in df.columns:
        missing_count = int(df[col].isna().sum())
        missing_values[col] = missing_count
    
    data_types = {}
    for col in df.columns:
        data_types[col] = str(df[col].dtype)
    
    unique_values = {}
    for col in df.columns:
        unique_count = int(df[col].nunique())
        unique_values[col] = unique_count
    
    stats = DataStatistics(
        rows=len(df),
        columns=len(df.columns),
        missing_values=missing_values,
        data_types=data_types,
        unique_values=unique_values,
        numeric_stats={}
    )
    
    # Calculate numeric statistics
    numeric_cols = df.select_dtypes(include=[np.number]).columns
    for col in numeric_cols:
        col_min = df[col].min()
        col_max = df[col].max()
        col_mean = df[col].mean()
        col_std = df[col].std()
        
        stats.numeric_stats[col] = {
            "min": float(col_min) if pd.notna(col_min) and np.isfinite(col_min) else 0.0,
            "max": float(col_max) if pd.notna(col_max) and np.isfinite(col_max) else 0.0,
            "mean": float(col_mean) if pd.notna(col_mean) and np.isfinite(col_mean) else 0.0,
            "std": float(col_std) if pd.notna(col_std) and np.isfinite(col_std) else 0.0
        }
    
    return stats

def clean_dataframe(df: pd.DataFrame, options: CleaningOptions) -> pd.DataFrame:
    """Apply cleaning operations to DataFrame"""
    result_df = df.copy()
    
    # Remove duplicates
    if options.remove_duplicates:
        result_df = result_df.drop_duplicates()
    
    # Handle missing values
    if options.handle_missing == "drop":
        result_df = result_df.dropna()
    elif options.handle_missing == "fill" and options.fill_value is not None:
        result_df = result_df.fillna(options.fill_value)
    
    # Rename columns
    if options.column_renames:
        result_df = result_df.rename(columns=options.column_renames)
    
    # Find and replace values
    if options.find_replace:
        for column, replacements in options.find_replace.items():
            if column in result_df.columns:
                for old_val, new_val in replacements.items():
                    result_df[column] = result_df[column].replace(old_val, new_val)
    
    # Trim whitespace
    if options.trim_whitespace:
        str_cols = result_df.select_dtypes(include=['object']).columns
        for col in str_cols:
            result_df[col] = result_df[col].astype(str).str.strip()
    
    # Convert data types
    if options.data_type_conversions:
        for column, new_type in options.data_type_conversions.items():
            if column in result_df.columns:
                try:
                    if new_type == "int":
                        result_df[column] = pd.to_numeric(result_df[column], errors='coerce').astype('Int64')
                    elif new_type == "float":
                        result_df[column] = pd.to_numeric(result_df[column], errors='coerce')
                    elif new_type == "datetime":
                        result_df[column] = pd.to_datetime(result_df[column], errors='coerce')
                    elif new_type == "string":
                        result_df[column] = result_df[column].astype(str)
                except Exception as e:
                    logging.warning(f"Failed to convert {column} to {new_type}: {e}")
    
    return result_df

def dataframe_to_export_format(df: pd.DataFrame, format_type: str) -> bytes:
    """Convert DataFrame to specified export format"""
    if format_type == "csv":
        return df.to_csv(index=False).encode('utf-8')
    elif format_type == "xlsx":
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            df.to_excel(writer, index=False)
        return buffer.getvalue()
    elif format_type == "json":
        return df.to_json(orient='records', indent=2).encode('utf-8')
    else:
        raise HTTPException(status_code=400, detail=f"Unsupported export format: {format_type}")

# API Routes
@api_router.get("/")
async def root():
    return {"message": "Data Cleaner API is running", "version": "1.0.0"}

@api_router.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    """Upload and store a data file"""
    try:
        # Validate file type
        file_ext = file.filename.split('.')[-1].lower()
        if file_ext not in ['csv', 'xlsx', 'json']:
            raise HTTPException(status_code=400, detail="Unsupported file type. Please upload CSV, XLSX, or JSON files.")
        
        # Generate unique file ID
        file_id = str(uuid.uuid4())
        file_path = UPLOAD_DIR / f"{file_id}.{file_ext}"
        
        # Save file
        content = await file.read()
        with open(file_path, "wb") as f:
            f.write(content)
        
        # Read file to validate and get preview
        df = read_file_to_dataframe(str(file_path), file_ext)
        
        # Store file info in database
        file_info = FileInfo(
            id=file_id,
            filename=file.filename,
            file_type=file_ext,
            size=len(content)
        )
        
        await db.files.insert_one(file_info.dict())
        
        # Return file info with preview data
        preview_data = df.head(10).fillna("").to_dict('records')
        statistics = calculate_statistics(df)
        
        return {
            "file_info": file_info.dict(),
            "preview_data": preview_data,
            "statistics": statistics.dict(),
            "columns": list(df.columns)
        }
        
    except Exception as e:
        logging.error(f"Upload error: {e}")
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

@api_router.get("/files")
async def get_uploaded_files():
    """Get list of all uploaded files"""
    try:
        files = await db.files.find().to_list(1000)
        return [FileInfo(**file_data) for file_data in files]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve files: {str(e)}")

@api_router.get("/file/{file_id}/data")
async def get_file_data(file_id: str, page: int = 0, page_size: int = 50):
    """Get paginated data from a specific file"""
    try:
        # Get file info from database
        file_data = await db.files.find_one({"id": file_id})
        if not file_data:
            raise HTTPException(status_code=404, detail="File not found")
        
        file_info = FileInfo(**file_data)
        file_path = UPLOAD_DIR / f"{file_id}.{file_info.file_type}"
        
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="File not found on disk")
        
        # Read file
        df = read_file_to_dataframe(str(file_path), file_info.file_type)
        
        # Apply pagination
        start_idx = page * page_size
        end_idx = start_idx + page_size
        paginated_df = df.iloc[start_idx:end_idx]
        
        return {
            "data": paginated_df.to_dict('records'),
            "total_rows": len(df),
            "page": page,
            "page_size": page_size,
            "total_pages": (len(df) + page_size - 1) // page_size,
            "columns": list(df.columns)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve file data: {str(e)}")

@api_router.post("/clean")
async def clean_data(file_id: str = Form(...), options: str = Form(...)):
    """Clean data based on provided options"""
    try:
        # Parse cleaning options
        cleaning_options = CleaningOptions(**json.loads(options))
        
        # Get file info
        file_data = await db.files.find_one({"id": file_id})
        if not file_data:
            raise HTTPException(status_code=404, detail="File not found")
        
        file_info = FileInfo(**file_data)
        file_path = UPLOAD_DIR / f"{file_id}.{file_info.file_type}"
        
        # Read and clean data
        df = read_file_to_dataframe(str(file_path), file_info.file_type)
        
        # Handle file merging if specified
        if cleaning_options.merge_files:
            dfs_to_merge = [df]
            for merge_file_id in cleaning_options.merge_files:
                merge_file_data = await db.files.find_one({"id": merge_file_id})
                if merge_file_data:
                    merge_file_info = FileInfo(**merge_file_data)
                    merge_file_path = UPLOAD_DIR / f"{merge_file_id}.{merge_file_info.file_type}"
                    merge_df = read_file_to_dataframe(str(merge_file_path), merge_file_info.file_type)
                    dfs_to_merge.append(merge_df)
            
            # Merge DataFrames
            df = pd.concat(dfs_to_merge, ignore_index=True, sort=False)
        
        # Apply cleaning operations
        cleaned_df = clean_dataframe(df, cleaning_options)
        
        # Save cleaned data
        cleaned_file_id = str(uuid.uuid4())
        cleaned_file_path = UPLOAD_DIR / f"{cleaned_file_id}_cleaned.csv"
        cleaned_df.to_csv(cleaned_file_path, index=False)
        
        # Calculate statistics for cleaned data
        cleaned_stats = calculate_statistics(cleaned_df)
        
        # Store cleaned file info
        cleaned_file_info = FileInfo(
            id=cleaned_file_id,
            filename=f"cleaned_{file_info.filename}",
            file_type="csv",
            size=cleaned_file_path.stat().st_size
        )
        
        await db.files.insert_one(cleaned_file_info.dict())
        
        return {
            "cleaned_file_id": cleaned_file_id,
            "original_rows": len(df),
            "cleaned_rows": len(cleaned_df),
            "preview_data": cleaned_df.head(10).to_dict('records'),
            "statistics": cleaned_stats.dict(),
            "columns": list(cleaned_df.columns)
        }
        
    except Exception as e:
        logging.error(f"Cleaning error: {e}")
        raise HTTPException(status_code=500, detail=f"Cleaning failed: {str(e)}")

@api_router.get("/download/{file_id}")
async def download_file(file_id: str, format: str = "csv"):
    """Download a file in specified format"""
    try:
        # Get file info
        file_data = await db.files.find_one({"id": file_id})
        if not file_data:
            raise HTTPException(status_code=404, detail="File not found")
        
        file_info = FileInfo(**file_data)
        
        # Check for cleaned file first
        cleaned_file_path = UPLOAD_DIR / f"{file_id}_cleaned.csv"
        if cleaned_file_path.exists():
            df = pd.read_csv(cleaned_file_path)
        else:
            original_file_path = UPLOAD_DIR / f"{file_id}.{file_info.file_type}"
            df = read_file_to_dataframe(str(original_file_path), file_info.file_type)
        
        # Convert to requested format
        file_content = dataframe_to_export_format(df, format)
        
        # Set appropriate content type and filename
        content_types = {
            "csv": "text/csv",
            "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "json": "application/json"
        }
        
        filename = f"{file_info.filename.split('.')[0]}.{format}"
        
        return Response(
            content=file_content,
            media_type=content_types[format],
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Download failed: {str(e)}")

@api_router.delete("/file/{file_id}")
async def delete_file(file_id: str):
    """Delete a file and its data"""
    try:
        # Get file info
        file_data = await db.files.find_one({"id": file_id})
        if not file_data:
            raise HTTPException(status_code=404, detail="File not found")
        
        file_info = FileInfo(**file_data)
        
        # Delete files from disk
        original_file_path = UPLOAD_DIR / f"{file_id}.{file_info.file_type}"
        cleaned_file_path = UPLOAD_DIR / f"{file_id}_cleaned.csv"
        
        if original_file_path.exists():
            original_file_path.unlink()
        if cleaned_file_path.exists():
            cleaned_file_path.unlink()
        
        # Delete from database
        await db.files.delete_one({"id": file_id})
        
        return {"message": "File deleted successfully"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Delete failed: {str(e)}")

# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()