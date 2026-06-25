import io
import pandas as pd
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
import openpyxl
from openpyxl.utils import get_column_letter

app = FastAPI(title="Financial Data Parser")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def read_root():
    return {"message": "Welcome to the Financial Data Parser API! The service is online and active."}

@app.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    keywords: str = Form(default="suspicious, fraud, unauthorized, error, anomaly")
):
    if file.filename and not file.filename.lower().endswith('.csv'):
        raise HTTPException(status_code=400, detail="Only .csv files are supported")

    # Read the uploaded CSV file
    contents = await file.read()
    
    # Load into pandas DataFrame
    try:
        df = pd.read_csv(io.BytesIO(contents))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error parsing CSV file: {str(e)}")
    
    user_keywords = [k.strip().lower() for k in keywords.split(',') if k.strip()]

    def highlight_numeric_outliers(s):
        # Process numeric series
        if pd.api.types.is_numeric_dtype(s):
            mean = s.mean()
            # New highly-sensitive threshold: 
            # If a value is 1.5x larger than the average, flag it!
            threshold = mean * 1.5
            
            return ['background-color: #fee2e2; color: #991b1b; font-weight: bold' if pd.notna(val) and val > threshold else '' for val in s]
        return [''] * len(s)

    def highlight_text(s):
        # Process text series
        if pd.api.types.is_string_dtype(s) or pd.api.types.is_object_dtype(s):
            return ['background-color: #fee2e2; color: #991b1b; font-weight: bold' if isinstance(val, str) and any(k in val.lower() for k in user_keywords) else '' for val in s]
        return [''] * len(s)

    try:
        # Apply numeric and text highlighting column by column
        styled_df = df.style.apply(highlight_numeric_outliers, axis=0).apply(highlight_text, axis=0)
    except Exception:
        styled_df = df

    # Create an in-memory buffer for the Excel file
    buffer = io.BytesIO()

    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
        styled_df.to_excel(writer, index=False, sheet_name='Anomaly Report')
        worksheet = writer.sheets['Anomaly Report']
        
        # Auto-adjust column widths for a premium, highly structured look
        for idx, col in enumerate(df.columns):
            max_len = max(df[col].astype(str).map(len).max(), len(str(col))) + 2
            worksheet.column_dimensions[get_column_letter(idx + 1)].width = min(max_len, 50)
        
    # Reset buffer position to the beginning before returning
    buffer.seek(0)
    
    # Generate the new filename (replace extension with .xlsx)
    original_filename = file.filename or "data.csv"
    base_name = original_filename.rsplit('.', 1)[0]
    excel_filename = f"{base_name}_anomalies.xlsx"
    
    # Return as a downloadable Excel file
    return StreamingResponse(
        buffer,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={excel_filename}"}
    )
