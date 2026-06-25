import io
import pandas as pd
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
import openpyxl
from openpyxl.utils import get_column_letter
from openpyxl.styles import PatternFill, Font, Alignment

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

    # Opaque ARGB formatting for heatmaps
    yellow_fill = PatternFill(start_color="FFFFEB9C", end_color="FFFFEB9C", fill_type="solid")
    yellow_font = Font(color="FF9C6500", bold=True)
    
    orange_fill = PatternFill(start_color="FFFFC7CE", end_color="FFFFC7CE", fill_type="solid")
    orange_font = Font(color="FF9C0006", bold=True)
    
    red_fill = PatternFill(start_color="FFFF9999", end_color="FFFF9999", fill_type="solid")
    red_font = Font(color="FF990000", bold=True)
    
    severe_fill = PatternFill(start_color="FF990000", end_color="FF990000", fill_type="solid")
    severe_font = Font(color="FFFFFFFF", bold=True)

    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Anomaly Report')
        worksheet = writer.sheets['Anomaly Report']
        
        # 1. Premium Features: Freeze Top Row & Add AutoFilter
        worksheet.freeze_panes = "A2"
        max_col_letter = get_column_letter(len(df.columns))
        max_row = len(df) + 1
        worksheet.auto_filter.ref = f"A1:{max_col_letter}{max_row}"
        
        # 2. Auto-adjust column widths
        for idx, col in enumerate(df.columns):
            max_len = max(df[col].astype(str).map(len).max(), len(str(col))) + 2
            worksheet.column_dimensions[get_column_letter(idx + 1)].width = min(max_len, 50)
            
        # 3. Find which columns are numeric vs text
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

        anomalous_rows = set()

        # 4. Apply Heatmap background colors
        for row in range(2, len(df) + 2):
            for col_idx in text_cols:
                cell = worksheet.cell(row=row, column=col_idx)
                if isinstance(cell.value, str):
                    if any(k in cell.value.lower() for k in user_keywords):
                        cell.fill = red_fill
                        cell.font = red_font
                        anomalous_rows.add(row)
            
            for col_idx in numeric_cols:
                cell = worksheet.cell(row=row, column=col_idx)
                val = cell.value
                if val is not None and isinstance(val, (int, float)):
                    mean = stats[col_idx]['mean']
                    
                    if val > (mean * 3.0):
                        cell.fill = severe_fill
                        cell.font = severe_font
                        anomalous_rows.add(row)
                    elif val > (mean * 2.0):
                        cell.fill = red_fill
                        cell.font = red_font
                        anomalous_rows.add(row)
                    elif val > (mean * 1.5):
                        cell.fill = orange_fill
                        cell.font = orange_font
                        anomalous_rows.add(row)
                    elif val > (mean * 1.2): # Slightly suspicious
                        cell.fill = yellow_fill
                        cell.font = yellow_font
                        anomalous_rows.add(row)

        # 5. Create Summary Dashboard Sheet
        dashboard = writer.book.create_sheet("Summary Dashboard", 0)
        dashboard.sheet_view.showGridLines = False
        
        dashboard.column_dimensions['A'].width = 25
        dashboard.column_dimensions['B'].width = 15
        
        title_cell = dashboard['A1']
        title_cell.value = "Financial Anomaly Dashboard"
        title_cell.font = Font(size=18, bold=True, color="FF2F5597")
        
        total_rows = len(df)
        anomaly_count = len(anomalous_rows)
        pct_anomalies = (anomaly_count / total_rows) * 100 if total_rows > 0 else 0
        
        dashboard['A3'] = "Total Transactions:"
        dashboard['B3'] = total_rows
        
        dashboard['A4'] = "Anomalies Detected:"
        dashboard['B4'] = anomaly_count
        
        dashboard['A5'] = "Suspicious Rate:"
        dashboard['B5'] = f"{pct_anomalies:.1f}%"
        
        for r in range(3, 6):
            dashboard[f'A{r}'].font = Font(bold=True)
            dashboard[f'B{r}'].alignment = Alignment(horizontal='left')
            if r in [4, 5]:
                color = "FF990000" if anomaly_count > 0 else "FF006100"
                dashboard[f'B{r}'].font = Font(bold=True, color=color)
            else:
                dashboard[f'B{r}'].font = Font(bold=True)
                
        # Set Dashboard as the active sheet when opened
        writer.book.active = 0
        
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
