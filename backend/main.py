import os
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Request, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from typing import List, Optional
import openai
from dotenv import load_dotenv
import json
from pathlib import Path
from backend.prompts import SYSTEM_PROMPT, EXAMPLE_LESSON_PLAN, EXAMPLE_RUBRIC

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
openai.api_key = OPENAI_API_KEY

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve static files (JS, CSS)
app.mount("/static", StaticFiles(directory="backend/static"), name="static")
# Serve templates (HTML)
templates = Jinja2Templates(directory="backend/templates")


class RubricRow(BaseModel):
    code: str
    indicator_description: str
    yes: str
    partial: str
    no: str

class RubricRequest(BaseModel):
    lesson_plan: str
    format: str  # "text" or "file"

@app.get("/", response_class=HTMLResponse)
def root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/generate-rubric", response_model=List[RubricRow])
async def generate_rubric(
    lesson_plan: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None),
    format: str = Form(...)
):
    if format not in ("text", "file"):
        raise HTTPException(status_code=400, detail="Invalid format. Use 'text' or 'file'.")
    if format == "file":
        if not file:
            raise HTTPException(status_code=400, detail="No file uploaded.")
        content = (await file.read()).decode("utf-8")
    else:
        if not lesson_plan:
            raise HTTPException(status_code=400, detail="No lesson plan provided.")
        content = lesson_plan

    user_prompt = f"""Create a lesson-specific fidelity rubric for the following lesson plan. Use ONLY evidence from this specific lesson plan.

**EXAMPLE FOR REFERENCE ONLY:**
Lesson Plan: {EXAMPLE_LESSON_PLAN}

Expected Rubric Format: {json.dumps(EXAMPLE_RUBRIC[:2], indent=2)}

**NOW CREATE RUBRIC FOR THIS LESSON PLAN:**
{content}

Generate the complete JSON rubric for indicators B1-B11:"""

    try:
        response = openai.chat.completions.create(
            model="gpt-4o",  # Using latest model
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.3,  # Slightly more flexible
            max_tokens=3000,  # Increased for complete rubrics
        )
        
        text = response.choices[0].message.content
        if text is None:
            raise HTTPException(status_code=500, detail="No response from OpenAI API.")
        
        # Clean up the response to extract JSON
        text = text.strip()
        
        # Try to find JSON array in the response
        import re
        json_match = re.search(r'\[\s*{.*?}\s*\]', text, re.DOTALL)
        if json_match:
            rubric_json = json.loads(json_match.group(0))
        else:
            # If no JSON array found, try to parse the whole response
            try:
                rubric_json = json.loads(text)
            except:
                # If that fails, try to extract content between ```json blocks
                json_code_match = re.search(r'```json\s*(.*?)\s*```', text, re.DOTALL)
                if json_code_match:
                    rubric_json = json.loads(json_code_match.group(1))
                else:
                    raise ValueError("Could not extract valid JSON from response")
        
        # Validate that we have all 11 indicators
        if len(rubric_json) != 11:
            # If missing indicators, fill them with basic structure
            existing_codes = {item.get('code') for item in rubric_json}
            for i in range(1, 12):
                code = f"B{i}"
                if code not in existing_codes:
                    rubric_json.append({
                        "code": code,
                        "indicator_description": f"Indicator {code} - please refer to official rubric",
                        "yes": "Evidence present in lesson plan",
                        "partial": "Limited evidence in lesson plan", 
                        "no": "No evidence in lesson plan"
                    })
        
        # Validate and return
        return [RubricRow(**row) for row in rubric_json[:11]]  # Ensure only 11 items
        
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=500, detail=f"Invalid JSON response: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Rubric generation failed: {str(e)}")

@app.post("/rubric-from-string", response_model=List[RubricRow])
async def rubric_from_string(payload: dict = Body(...)):
    lesson_plan = payload.get("lesson_plan")
    if not lesson_plan or not isinstance(lesson_plan, str):
        raise HTTPException(status_code=400, detail="Missing or invalid 'lesson_plan' in request body.")
    return await _generate_rubric_from_content(lesson_plan)

@app.post("/rubric-from-filepath", response_model=List[RubricRow])
async def rubric_from_filepath(payload: dict = Body(...)):
    file_path = payload.get("file_path")
    if not file_path or not isinstance(file_path, str):
        raise HTTPException(status_code=400, detail="Missing or invalid 'file_path' in request body.")
    try:
        content = Path(file_path).read_text(encoding="utf-8")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Could not read file: {str(e)}")
    return await _generate_rubric_from_content(content)

# --- Internal helper for rubric generation ---
async def _generate_rubric_from_content(content: str):
    import re
    user_prompt = f"""Create a lesson-specific fidelity rubric for the following lesson plan. Use ONLY evidence from this specific lesson plan.\n\n**EXAMPLE FOR REFERENCE ONLY:**\nLesson Plan: {EXAMPLE_LESSON_PLAN}\n\nExpected Rubric Format: {json.dumps(EXAMPLE_RUBRIC[:2], indent=2)}\n\n**NOW CREATE RUBRIC FOR THIS LESSON PLAN:**\n{content}\n\nGenerate the complete JSON rubric for indicators B1-B11:"""
    try:
        response = openai.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.3,
            max_tokens=3000,
        )
        text = response.choices[0].message.content
        if text is None:
            raise HTTPException(status_code=500, detail="No response from OpenAI API.")
        text = text.strip()
        json_match = re.search(r'\[\s*{.*?}\s*\]', text, re.DOTALL)
        if json_match:
            rubric_json = json.loads(json_match.group(0))
        else:
            try:
                rubric_json = json.loads(text)
            except:
                json_code_match = re.search(r'```json\s*(.*?)\s*```', text, re.DOTALL)
                if json_code_match:
                    rubric_json = json.loads(json_code_match.group(1))
                else:
                    raise ValueError("Could not extract valid JSON from response")
        if len(rubric_json) != 11:
            existing_codes = {item.get('code') for item in rubric_json}
            for i in range(1, 12):
                code = f"B{i}"
                if code not in existing_codes:
                    rubric_json.append({
                        "code": code,
                        "indicator_description": f"Indicator {code} - please refer to official rubric",
                        "yes": "Evidence present in lesson plan",
                        "partial": "Limited evidence in lesson plan",
                        "no": "No evidence in lesson plan"
                    })
        return [RubricRow(**row) for row in rubric_json[:11]]
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=500, detail=f"Invalid JSON response: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Rubric generation failed: {str(e)}")

@app.get("/sample-lesson-plan")
def get_sample_lesson_plan():
    return {"lesson_plan": EXAMPLE_LESSON_PLAN, "rubric": EXAMPLE_RUBRIC}

@app.get("/health")
def health_check():
    """
    Health check endpoint to verify if the server is running and healthy.
    Returns status information about the application.
    """
    return {
        "status": "healthy",
        "message": "Lesson Fidelity Rubric Generator is running",
        "timestamp": "2024-01-01T00:00:00Z",
        "version": "1.0.0",
        "endpoints": {
            "health": "/health",
            "home": "/",
            "generate_rubric": "/generate-rubric",
            "sample_lesson": "/sample-lesson-plan"
        }
    }