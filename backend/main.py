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
    expose_headers=["Content-Disposition"],
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

    # Create an in-memory buffer for the Excel file
    buffer = io.BytesIO()

    from openpyxl.styles import PatternFill, Font
    # Using 100% Opaque ARGB formatting
    red_fill = PatternFill(start_color="FFFEE2E2", end_color="FFFEE2E2", fill_type="solid")
    red_font = Font(color="FF991B1B", bold=True)

    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Anomaly Report')
        worksheet = writer.sheets['Anomaly Report']
        
        # 1. Auto-adjust column widths
        for idx, col in enumerate(df.columns):
            max_len = max(df[col].astype(str).map(len).max(), len(str(col))) + 2
            worksheet.column_dimensions[get_column_letter(idx + 1)].width = min(max_len, 50)
            
        # 2. Find which columns are numeric vs text
        numeric_cols = []
        text_cols = []
        stats = {}
        for idx, col in enumerate(df.columns):
            if pd.api.types.is_numeric_dtype(df[col]):
                numeric_cols.append(idx + 1)
                stats[idx + 1] = {
                    'mean': df[col].mean(),
                    'std': df[col].std()
                }
            elif pd.api.types.is_string_dtype(df[col]) or pd.api.types.is_object_dtype(df[col]):
                text_cols.append(idx + 1)

        # 3. Apply opaque background colors directly (bypassing pandas styling bugs)
        for row in range(2, len(df) + 2):
            for col_idx in text_cols:
                cell = worksheet.cell(row=row, column=col_idx)
                if isinstance(cell.value, str):
                    if any(k in cell.value.lower() for k in user_keywords):
                        cell.fill = red_fill
                        cell.font = red_font
            
            for col_idx in numeric_cols:
                cell = worksheet.cell(row=row, column=col_idx)
                val = cell.value
                if val is not None and isinstance(val, (int, float)):
                    mean = stats[col_idx]['mean']
                    threshold = mean * 1.5
                    if val > threshold:
                        cell.fill = red_fill
                        cell.font = red_font
        
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
