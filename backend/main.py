import io
import pandas as pd
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
import openpyxl
from openpyxl.utils import get_column_letter
from openpyxl.styles import PatternFill, Font, Alignment, Border, Side
from openpyxl.chart import PieChart3D, Reference
from openpyxl.chart.label import DataLabelList

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
        
        # Sort by Date if available
        date_col = None
        for col in df.columns:
            if 'date' in str(col).lower() or 'time' in str(col).lower():
                date_col = col
                break
                
        if date_col:
            df[date_col] = pd.to_datetime(df[date_col], errors='coerce')
            df = df.sort_values(by=date_col).reset_index(drop=True)
            df[date_col] = df[date_col].dt.strftime('%Y-%m-%d %H:%M:%S').fillna(df[date_col])
            
        # Rapid Succession Detection (3 or more consecutive within 5%)
        rapid_warnings = 0
        for col in df.columns:
            if pd.api.types.is_numeric_dtype(df[col]):
                vals = df[col].values
                streak = 1
                for i in range(1, len(vals)):
                    prev = vals[i-1]
                    curr = vals[i]
                    if pd.isna(prev) or pd.isna(curr) or prev == 0:
                        if streak >= 3:
                            rapid_warnings += 1
                        streak = 1
                        continue
                    diff_pct = abs(curr - prev) / abs(prev)
                    if diff_pct <= 0.05:
                        streak += 1
                    else:
                        if streak >= 3:
                            rapid_warnings += 1
                        streak = 1
                if streak >= 3:
                    rapid_warnings += 1

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
            
        # 3. Find which columns are numeric vs text and compute robust baseline
        numeric_cols = []
        text_cols = []
        stats = {}
        for idx, col in enumerate(df.columns):
            if pd.api.types.is_numeric_dtype(df[col]):
                numeric_cols.append(idx + 1)
                abs_data = df[col].abs()
                q10 = abs_data.quantile(0.10)
                median = abs_data.median()
                mean = abs_data.mean()
                
                # Dynamic floor based on the median to prevent micro-transactions from burying normal purchases.
                # The vast majority of purchases center around the median, so we use 25% of the median as a robust floor.
                dynamic_floor = median * 0.25 if median > 0 else 1.0
                base_val = max(q10, dynamic_floor)
                
                if base_val == 0:
                    base_val = mean if mean > 0 else 1.0
                    
                stats[idx + 1] = {
                    'base_val': base_val
                }
            elif pd.api.types.is_string_dtype(df[col]) or pd.api.types.is_object_dtype(df[col]):
                text_cols.append(idx + 1)

        # Track severity categories for pie charts
        severity_counts = {
            "Severe": 0,
            "Suspicious": 0,
            "Slight": 0,
            "Text": 0,
            "Clean": 0
        }

        # 4. Apply Heatmap background colors
        for row in range(2, len(df) + 2):
            row_severity = "Clean"
            
            # Check Text Anomalies
            for col_idx in text_cols:
                cell = worksheet.cell(row=row, column=col_idx)
                if isinstance(cell.value, str):
                    if any(k in cell.value.lower() for k in user_keywords):
                        cell.fill = red_fill
                        cell.font = red_font
                        row_severity = "Text"
            
            # Check Numeric Anomalies (Overrides text if severity is higher)
            for col_idx in numeric_cols:
                cell = worksheet.cell(row=row, column=col_idx)
                val = cell.value
                if val is not None and isinstance(val, (int, float)):
                    base_val = stats[col_idx]['base_val']
                    ratio = abs(val) / base_val
                    
                    if ratio >= 5.0:
                        cell.fill = severe_fill
                        cell.font = severe_font
                        row_severity = "Severe"
                    elif ratio >= 2.5:
                        cell.fill = red_fill
                        cell.font = red_font
                        if row_severity != "Severe":
                            row_severity = "Suspicious"
                    elif ratio >= 1.5:
                        cell.fill = yellow_fill
                        cell.font = yellow_font
                        if row_severity not in ["Severe", "Suspicious"]:
                            row_severity = "Slight"
                            
            severity_counts[row_severity] += 1

        # 5. Create Summary Dashboard Sheet
        dashboard = writer.book.create_sheet("Summary Dashboard", 0)
        dashboard.sheet_view.showGridLines = False
        
        dashboard.column_dimensions['A'].width = 25
        dashboard.column_dimensions['B'].width = 15
        dashboard.column_dimensions['C'].width = 15
        dashboard.column_dimensions['D'].width = 20
        
        title_cell = dashboard['A1']
        title_cell.value = "Financial Anomaly Dashboard"
        title_cell.font = Font(size=18, bold=True, color="FF2F5597")
        
        total_rows = len(df)
        total_anomalies = total_rows - severity_counts["Clean"]
        pct_anomalies = (total_anomalies / total_rows) * 100 if total_rows > 0 else 0
        
        dashboard['A3'] = "Total Transactions:"
        dashboard['B3'] = total_rows
        
        dashboard['A4'] = "Total Anomalies:"
        dashboard['B4'] = total_anomalies
        
        dashboard['A5'] = "Suspicious Rate:"
        dashboard['B5'] = f"{pct_anomalies:.1f}%"
        
        dashboard['A6'] = "Rapid Successions (Warnings):"
        dashboard['B6'] = rapid_warnings

        for r in range(3, 7):
            dashboard[f'A{r}'].font = Font(bold=True)
            dashboard[f'B{r}'].alignment = Alignment(horizontal='left')
            if r in [4, 5]:
                color = "FF990000" if total_anomalies > 0 else "FF006100"
                dashboard[f'B{r}'].font = Font(bold=True, color=color)
            elif r == 6:
                color = "FF9C0006" if rapid_warnings > 0 else "FF006100"
                dashboard[f'B{r}'].font = Font(bold=True, color=color)
            else:
                dashboard[f'B{r}'].font = Font(bold=True)
                
        # 6. Breakdown Table Formatting
        dashboard['A9'] = "Anomaly Type"
        dashboard['B9'] = "Count"
        dashboard['C9'] = "% of Total"
        dashboard['D9'] = "% of Anomalies"
        
        thin_border = Border(left=Side(style='thin'), right=Side(style='thin'), top=Side(style='thin'), bottom=Side(style='thin'))
        
        for col in ['A', 'B', 'C', 'D']:
            dashboard[f'{col}9'].font = Font(bold=True, color="FFFFFFFF")
            dashboard[f'{col}9'].fill = PatternFill(start_color="FF2F5597", end_color="FF2F5597", fill_type="solid")
            dashboard[f'{col}9'].alignment = Alignment(horizontal="center", vertical="center")
            dashboard[f'{col}9'].border = thin_border
            
        categories = ["Severe", "Suspicious", "Slight", "Text", "Clean"]
        for i, cat in enumerate(categories):
            row = 10 + i
            count = severity_counts[cat]
            pct_total = (count / total_rows) if total_rows > 0 else 0
            pct_anom = (count / total_anomalies) if (total_anomalies > 0 and cat != "Clean") else 0
            
            dashboard[f'A{row}'] = cat
            dashboard[f'B{row}'] = count
            dashboard[f'C{row}'] = pct_total
            dashboard[f'C{row}'].number_format = '0.0%'
            
            if cat == "Clean":
                dashboard[f'D{row}'] = "N/A"
            else:
                dashboard[f'D{row}'] = pct_anom
                dashboard[f'D{row}'].number_format = '0.0%'
                
            # Apply borders and alignment
            for col in ['A', 'B', 'C', 'D']:
                cell = dashboard[f'{col}{row}']
                cell.border = thin_border
                if col in ['B', 'C', 'D']:
                    cell.alignment = Alignment(horizontal="center")
                
        # 7. Add Pie Charts
        # Chart 1: Whole Dataset
        pie1 = PieChart3D()
        pie1.title = "Dataset Breakdown (Whole Set)"
        labels1 = Reference(dashboard, min_col=1, min_row=10, max_row=14)
        data1 = Reference(dashboard, min_col=2, min_row=9, max_row=14)
        pie1.add_data(data1, titles_from_data=True)
        pie1.set_categories(labels1)
        pie1.dataLabels = DataLabelList()
        pie1.dataLabels.showSerName = False
        pie1.dataLabels.showVal = False
        pie1.dataLabels.showCatName = True
        pie1.dataLabels.showPercent = True
        pie1.legend = None
        pie1.width = 12
        pie1.height = 8
        dashboard.add_chart(pie1, "F2")
        
        # Chart 2: Anomaly Distribution (Only if anomalies exist)
        if total_anomalies > 0:
            pie2 = PieChart3D()
            pie2.title = "Anomaly Distribution (Anomalies Only)"
            labels2 = Reference(dashboard, min_col=1, min_row=10, max_row=13) # Exclude Clean
            data2 = Reference(dashboard, min_col=2, min_row=9, max_row=13)
            pie2.add_data(data2, titles_from_data=True)
            pie2.set_categories(labels2)
            pie2.dataLabels = DataLabelList()
            pie2.dataLabels.showSerName = False
            pie2.dataLabels.showVal = False
            pie2.dataLabels.showCatName = True
            pie2.dataLabels.showPercent = True
            pie2.legend = None
            pie2.width = 12
            pie2.height = 8
            dashboard.add_chart(pie2, "F17")
                
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
