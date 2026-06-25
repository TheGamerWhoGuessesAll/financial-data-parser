import io
import pandas as pd
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Financial Data Parser")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    if file.filename and not file.filename.lower().endswith('.csv'):
        raise HTTPException(status_code=400, detail="Only .csv files are supported")

    # Read the uploaded CSV file
    contents = await file.read()
    
    # Load into pandas DataFrame
    try:
        df = pd.read_csv(io.BytesIO(contents))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error parsing CSV file: {str(e)}")
    
    # Create an in-memory buffer for the Excel file
    buffer = io.BytesIO()
    
    # Write DataFrame to buffer as Excel
    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
        df.to_excel(writer, index=False)
        
    # Reset buffer position to the beginning before returning
    buffer.seek(0)
    
    # Generate the new filename (replace extension with .xlsx)
    original_filename = file.filename or "data.csv"
    base_name = original_filename.rsplit('.', 1)[0]
    excel_filename = f"{base_name}.xlsx"
    
    # Return as a downloadable Excel file
    return StreamingResponse(
        buffer,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={excel_filename}"}
    )
