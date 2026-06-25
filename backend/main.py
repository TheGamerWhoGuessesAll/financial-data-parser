import io
import os
import json
import uuid
import asyncio
import pandas as pd
import pdfplumber
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, BackgroundTasks, Depends, Request
from fastapi.responses import StreamingResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime, timedelta
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from passlib.context import CryptContext
import jwt
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi.security import OAuth2PasswordBearer
from fastapi import Depends, Request

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


# Database Setup
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./test.db")
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)

Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Auth Setup
SECRET_KEY = os.getenv("SECRET_KEY", "super-secret-key-for-jwt-do-not-share")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7 # 7 days

import bcrypt
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

def verify_password(plain_password, hashed_password):
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))

def get_password_hash(password):
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=401,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except jwt.PyJWTError:
        raise credentials_exception
        
    user = db.query(User).filter(User.email == email).first()
    if user is None:
        raise credentials_exception
    return user

# Pydantic Models
class UserCreate(BaseModel):
    email: str
    password: str

class UserLogin(BaseModel):
    email: str
    password: str

# Rate Limiter Setup
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

@app.post("/signup")
def signup(request: Request, user: UserCreate, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.email == user.email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    hashed_password = get_password_hash(user.password)
    new_user = User(email=user.email, hashed_password=hashed_password)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    access_token = create_access_token(data={"sub": new_user.email})
    return {"access_token": access_token, "token_type": "bearer"}

@app.post("/login")
def login(request: Request, user: UserLogin, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.email == user.email).first()
    if not db_user or not verify_password(user.password, db_user.hashed_password):
        raise HTTPException(status_code=401, detail="Incorrect email or password")
    access_token = create_access_token(data={"sub": db_user.email})
    return {"access_token": access_token, "token_type": "bearer"}

TASK_STORE = {}


@app.post("/upload")
async def upload_file(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    keywords: str = Form(default="suspicious, fraud, unauthorized, error, anomaly"),
    current_user: User = Depends(get_current_user)
):
    is_pdf = file.filename and file.filename.lower().endswith('.pdf')
    is_csv = file.filename and file.filename.lower().endswith('.csv')
    
    if not (is_pdf or is_csv):
        raise HTTPException(status_code=400, detail="Only .csv and .pdf files are supported")

    # Read the uploaded file
    contents = await file.read()
    
    task_id = str(uuid.uuid4())
    TASK_STORE[task_id] = {
        "status": "processing",
        "progress": 0,
        "message": "Initializing task...",
        "result": None,
        "filename": file.filename or "data.csv",
        "user_email": current_user.email
    }
    
    background_tasks.add_task(process_file_task, task_id, contents, is_csv, is_pdf, keywords)
    return {"task_id": task_id}

@app.get("/status/{task_id}")
async def get_status(task_id: str, current_user: User = Depends(get_current_user)):
    if task_id not in TASK_STORE or TASK_STORE[task_id].get("user_email") != current_user.email:
        raise HTTPException(status_code=404, detail="Task not found")
    return {
        "status": TASK_STORE[task_id]["status"],
        "progress": TASK_STORE[task_id]["progress"],
        "message": TASK_STORE[task_id]["message"]
    }

@app.get("/download/{task_id}")
async def download_file(task_id: str, current_user: User = Depends(get_current_user)):
    if task_id not in TASK_STORE or TASK_STORE[task_id].get("user_email") != current_user.email:
        raise HTTPException(status_code=404, detail="Task not found")
    
    task_data = TASK_STORE[task_id]
    if task_data["status"] != "completed":
        raise HTTPException(status_code=400, detail="Task not completed yet")
        
    buffer = io.BytesIO(task_data["result"])
    buffer.seek(0)
    
    original_filename = task_data["filename"]
    base_name = original_filename.rsplit('.', 1)[0]
    excel_filename = f"{base_name}_anomalies.xlsx"
    
    del TASK_STORE[task_id] # Clean up RAM
    
    return StreamingResponse(
        buffer,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={excel_filename}"}
    )

async def process_file_task(task_id: str, contents: bytes, is_csv: bool, is_pdf: bool, keywords: str):
    try:
        TASK_STORE[task_id]["message"] = "Extracting data..."
        TASK_STORE[task_id]["progress"] = 10
        
        if is_csv:
            df = pd.read_csv(io.BytesIO(contents))
        else:
            all_rows = []
            with pdfplumber.open(io.BytesIO(contents)) as pdf:
                for page in pdf.pages:
                    tables = page.extract_tables()
                    for table in tables:
                        for row in table:
                            if any(cell and str(cell).strip() for cell in row):
                                all_rows.append(row)
            if not all_rows:
                raise ValueError("No tabular data found in PDF")
            df = pd.DataFrame(all_rows[1:], columns=all_rows[0])
            for col in df.columns:
                if pd.api.types.is_string_dtype(df[col]):
                    df[col] = df[col].astype(str).str.strip()
                    try:
                        clean_col = df[col].str.replace('$', '', regex=False).str.replace(',', '', regex=False).str.replace(' ', '', regex=False)
                        num_col = pd.to_numeric(clean_col)
                        if num_col.notna().sum() > (len(df) * 0.3):
                            df[col] = num_col
                    except:
                        pass
        
        TASK_STORE[task_id]["message"] = "Cleaning data & running Math Engine..."
        TASK_STORE[task_id]["progress"] = 30
        
        # Dynamically scan contents for Date/Time format
        date_col = None
        for col in df.columns:
            if pd.api.types.is_datetime64_any_dtype(df[col]):
                date_col = col
                break
            
            if pd.api.types.is_string_dtype(df[col]) or pd.api.types.is_object_dtype(df[col]):
                sample_idx = df[col].first_valid_index()
                if sample_idx is not None:
                    sample_val = str(df[col].loc[sample_idx])
                    if any(c in sample_val for c in ['-', '/', ':']):
                        try:
                            pd.to_datetime(sample_val)
                            parsed_col = pd.to_datetime(df[col], errors='coerce')
                            if parsed_col.notna().sum() > (df[col].notna().sum() * 0.5):
                                date_col = col
                                df[date_col] = parsed_col
                                break
                        except Exception:
                            pass
                
        if date_col:
            if not pd.api.types.is_datetime64_any_dtype(df[date_col]):
                df[date_col] = pd.to_datetime(df[date_col], errors='coerce')
                
            df = df.sort_values(by=date_col).reset_index(drop=True)
            df[date_col] = df[date_col].dt.strftime('%Y-%m-%d %H:%M:%S').fillna(df[date_col])
            
        # Rapid Succession Detection
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

        user_keywords = [k.strip().lower() for k in keywords.split(',') if k.strip()]

        # AI Contextual Assessment
        ai_assessments = ["AI Pending"] * len(df)
        
        TASK_STORE[task_id]["message"] = "Connecting to Gemini AI..."
        TASK_STORE[task_id]["progress"] = 40
            
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            ai_assessments = ["API Key Missing"] * len(df)
        else:
            try:
                from google import genai
                from google.genai import types
                
                client = genai.Client(api_key=api_key)
                desc_col = None
                amt_col = None
                for col in df.columns:
                    if pd.api.types.is_numeric_dtype(df[col]) and amt_col is None:
                        amt_col = col
                    if (pd.api.types.is_string_dtype(df[col]) or pd.api.types.is_object_dtype(df[col])) and date_col != col:
                        desc_col = col
                
                if desc_col and amt_col:
                    batch_data = []
                    for idx, row in df.iterrows():
                        batch_data.append({
                            "id": idx,
                            "desc": str(row[desc_col]),
                            "amount": float(row[amt_col]) if not pd.isna(row[amt_col]) else 0.0
                        })
                    
                    batch_size = 50
                    chunks = [batch_data[i:i+batch_size] for i in range(0, len(batch_data), batch_size)]
                    
                    TASK_STORE[task_id]["message"] = f"AI Analyzing {len(df)} transactions concurrently..."
                    TASK_STORE[task_id]["progress"] = 50
                    
                    # Limit concurrency to 1 to completely avoid Free Tier burst rate limits
                    semaphore = asyncio.Semaphore(1)
                    
                    async def process_chunk(chunk):
                        async with semaphore:
                            prompt = f"""
                            You are an expert fraud analyst. Analyze the following list of transactions.
                            Identify any contextual anomalies. A contextual anomaly is:
                            1. A transaction where the AMOUNT is highly unusual for the DESCRIPTION (e.g., spending $500 at a 'Candy Shop').
                            2. A transaction where the DESCRIPTION is nonsensical, a single letter, or obviously fake (e.g., 'a', 'b', 'x', 'test').
                            
                            You do NOT need to flag transactions just because the number is large (e.g. $2000 for 'Rent' is normal).
                            
                            Return a JSON object mapping the transaction 'id' to a string assessment. 
                            If it's normal, map it to "Clean".
                            If it's suspicious, map it to a short explanation like "Fraud: $500 is extremely high for a Candy Shop" or "Fraud: 'a' is a highly suspicious and nonsensical merchant name."
                            
                            Transactions:
                            {json.dumps(chunk)}
                            """
                            
                            last_error = "Unknown error"
                            for attempt in range(3):
                                try:
                                    # Use the asynchronous client
                                    response = await client.aio.models.generate_content(
                                        model='gemini-1.5-flash-8b',
                                        contents=prompt,
                                        config=types.GenerateContentConfig(
                                            response_mime_type="application/json",
                                        ),
                                    )
                                    text = response.text
                                    if text.startswith("```json"):
                                        text = text.replace("```json", "").replace("```", "").strip()
                                    elif text.startswith("```"):
                                        text = text.replace("```", "").strip()
                                        
                                    parsed = json.loads(text)
                                    if parsed is None:
                                        parsed = {}
                                    return parsed
                                except Exception as e:
                                    last_error = str(e)
                                    if hasattr(e, 'message'):
                                        last_error = e.message
                                    if attempt < 2:
                                        await asyncio.sleep(2 ** attempt)
                                    else:
                                        return {str(item["id"]): f"AI Error: {last_error}" for item in chunk}
                            
                            return {str(item["id"]): f"AI Error: {last_error}" for item in chunk}
                    
                    tasks = [process_chunk(chunk) for chunk in chunks]
                    results = await asyncio.gather(*tasks)
                    
                    for assessments in results:
                        for idx_str, text in assessments.items():
                            idx_int = int(idx_str)
                            if 0 <= idx_int < len(ai_assessments):
                                ai_assessments[idx_int] = text
                else:
                    ai_assessments = ["Missing Amt/Desc Col"] * len(df)
            except Exception as e:
                err_msg = str(e)
                if hasattr(e, 'message'):
                    err_msg = e.message
                ai_assessments = [f"AI Error (Outer): {type(e).__name__} - {err_msg}"] * len(df)
                
        df['AI Context Assessment'] = ai_assessments

        TASK_STORE[task_id]["message"] = "Generating Excel Report..."
        TASK_STORE[task_id]["progress"] = 80

        # Create an in-memory buffer for the Excel file
        buffer = io.BytesIO()

        # Formatting
        yellow_fill = PatternFill(start_color="FFFFEB9C", end_color="FFFFEB9C", fill_type="solid")
        yellow_font = Font(color="FF9C6500", bold=True)
        orange_fill = PatternFill(start_color="FFFFC7CE", end_color="FFFFC7CE", fill_type="solid")
        orange_font = Font(color="FF9C0006", bold=True)
        red_fill = PatternFill(start_color="FFFF9999", end_color="FFFF9999", fill_type="solid")
        red_font = Font(color="FF990000", bold=True)
        severe_fill = PatternFill(start_color="FF990000", end_color="FF990000", fill_type="solid")
        severe_font = Font(color="FFFFFFFF", bold=True)
        purple_fill = PatternFill(start_color="FFCCCCFF", end_color="FFCCCCFF", fill_type="solid")
        purple_font = Font(color="FF333399", bold=True)

        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Anomaly Report')
            worksheet = writer.sheets['Anomaly Report']
            
            worksheet.freeze_panes = "A2"
            max_col_letter = get_column_letter(len(df.columns))
            max_row = len(df) + 1
            worksheet.auto_filter.ref = f"A1:{max_col_letter}{max_row}"
            
            ai_col_idx = df.columns.get_loc('AI Context Assessment') + 1
            
            for idx, col in enumerate(df.columns):
                max_len = max(df[col].astype(str).map(len).max(), len(str(col))) + 2
                worksheet.column_dimensions[get_column_letter(idx + 1)].width = min(max_len, 50)
                
            numeric_cols = []
            text_cols = []
            stats = {}
            for idx, col in enumerate(df.columns):
                if col == 'AI Context Assessment':
                    continue
                if pd.api.types.is_numeric_dtype(df[col]):
                    numeric_cols.append(idx + 1)
                    abs_data = df[col].abs()
                    valid_data = abs_data[abs_data > 0]
                    
                    if len(valid_data) >= 4:
                        q1 = valid_data.quantile(0.25)
                        q3 = valid_data.quantile(0.75)
                        iqr = q3 - q1
                        if iqr == 0:
                            iqr = valid_data.mean() * 0.10
                        base_val = q3 + (1.5 * iqr)
                    else:
                        base_val = valid_data.median() + (valid_data.mean() * 0.50) if not valid_data.empty else 1.0
                    
                    if pd.isna(base_val) or base_val <= 0:
                        base_val = valid_data.mean() if not valid_data.empty and valid_data.mean() > 0 else 1.0
                        
                    stats[idx + 1] = {'base_val': base_val}
                elif pd.api.types.is_string_dtype(df[col]) or pd.api.types.is_object_dtype(df[col]):
                    text_cols.append(idx + 1)

            severity_counts = {
                "Severe": 0, "Suspicious": 0, "Slight": 0, 
                "Text": 0, "Clean": 0, "AI Fraud": 0
            }

            for row in range(2, len(df) + 2):
                row_severity = "Clean"
                
                for col_idx in text_cols:
                    cell = worksheet.cell(row=row, column=col_idx)
                    if isinstance(cell.value, str):
                        if any(k in cell.value.lower() for k in user_keywords):
                            cell.fill = red_fill
                            cell.font = red_font
                            row_severity = "Text"
                
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
                                
                # AI Check
                ai_cell = worksheet.cell(row=row, column=ai_col_idx)
                ai_val = str(ai_cell.value).lower()
                is_normal = "clean" in ai_val or "missing" in ai_val or "disabled" in ai_val or "error" in ai_val
                
                if not is_normal:
                    ai_cell.fill = purple_fill
                    ai_cell.font = purple_font
                    if row_severity == "Clean" or row_severity == "Slight":
                        row_severity = "AI Fraud"
                        
                severity_counts[row_severity] += 1

            dashboard = writer.book.create_sheet("Summary Dashboard", 0)
            dashboard.sheet_view.showGridLines = False
            
            dashboard.column_dimensions['A'].width = 25
            dashboard.column_dimensions['B'].width = 15
            dashboard.column_dimensions['C'].width = 15
            dashboard.column_dimensions['D'].width = 20
            
            title_cell = dashboard['A1']
            title_cell.value = "Financial Anomaly Dashboard"
            title_cell.font = Font(size=18, bold=True, color="FF2F5597")
            
            warning_cell = dashboard['C1']
            warning_cell.value = "(Note: May be inaccurate for small datasets)"
            warning_cell.font = Font(size=10, italic=True, color="FFFF0000")
            
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
            dashboard['A7'] = "AI Context Anomalies:"
            dashboard['B7'] = severity_counts["AI Fraud"]

            for r in range(3, 8):
                dashboard[f'A{r}'].font = Font(bold=True)
                dashboard[f'B{r}'].alignment = Alignment(horizontal='left')
                if r in [4, 5]:
                    color = "FF990000" if total_anomalies > 0 else "FF006100"
                    dashboard[f'B{r}'].font = Font(bold=True, color=color)
                elif r == 6:
                    color = "FF9C0006" if rapid_warnings > 0 else "FF006100"
                    dashboard[f'B{r}'].font = Font(bold=True, color=color)
                elif r == 7:
                    color = "FF333399" if severity_counts["AI Fraud"] > 0 else "FF006100"
                    dashboard[f'B{r}'].font = Font(bold=True, color=color)
                else:
                    dashboard[f'B{r}'].font = Font(bold=True)
                    
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
                
            categories = ["Severe", "Suspicious", "Slight", "Text", "AI Fraud", "Clean"]
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
                    
                for col in ['A', 'B', 'C', 'D']:
                    cell = dashboard[f'{col}{row}']
                    cell.border = thin_border
                    if col in ['B', 'C', 'D']:
                        cell.alignment = Alignment(horizontal="center")
                    
            pie1 = PieChart3D()
            pie1.title = "Dataset Breakdown (Whole Set)"
            labels1 = Reference(dashboard, min_col=1, min_row=10, max_row=15)
            data1 = Reference(dashboard, min_col=2, min_row=9, max_row=15)
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
            
            if total_anomalies > 0:
                pie2 = PieChart3D()
                pie2.title = "Anomaly Distribution (Anomalies Only)"
                labels2 = Reference(dashboard, min_col=1, min_row=10, max_row=14)
                data2 = Reference(dashboard, min_col=2, min_row=9, max_row=14)
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
                    
            writer.book.active = 0
            
        TASK_STORE[task_id]["message"] = "Completed!"
        TASK_STORE[task_id]["progress"] = 100
        TASK_STORE[task_id]["result"] = buffer.getvalue()
        TASK_STORE[task_id]["status"] = "completed"

    except Exception as e:
        print(f"Error in background task: {e}")
        TASK_STORE[task_id]["status"] = "error"
        TASK_STORE[task_id]["message"] = f"Error: {str(e)}"


import os
if os.path.exists("frontend"):
    app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")
elif os.path.exists("../frontend"):
    app.mount("/", StaticFiles(directory="../frontend", html=True), name="frontend")
