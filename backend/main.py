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

# New models for survey format
class Option(BaseModel):
    label: str
    value: str
    score_type: str
    order: int

class Question(BaseModel):
    prompt: str
    order: int
    options: List[Option]

class SurveyRubric(BaseModel):
    questions: List[Question]

class RubricRequest(BaseModel):
    lesson_plan: str
    format: str  # "text" or "file"

@app.get("/", response_class=HTMLResponse)
def root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/generate-rubric", response_model=SurveyRubric)
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

    return await _generate_rubric_from_content(content)

@app.post("/rubric-from-string", response_model=SurveyRubric)
async def rubric_from_string(payload: dict = Body(...)):
    lesson_plan = payload.get("lesson_plan")
    if not lesson_plan or not isinstance(lesson_plan, str):
        raise HTTPException(status_code=400, detail="Missing or invalid 'lesson_plan' in request body.")
    return await _generate_rubric_from_content(lesson_plan)

@app.post("/rubric-from-filepath", response_model=SurveyRubric)
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
    user_prompt = f"""Create a lesson-specific fidelity rubric for the following lesson plan. Use ONLY evidence from this specific lesson plan.

**EXAMPLE FOR REFERENCE ONLY:**
Lesson Plan: {EXAMPLE_LESSON_PLAN}

Expected Rubric Format: {json.dumps(EXAMPLE_RUBRIC, indent=2)}

**NOW CREATE RUBRIC FOR THIS LESSON PLAN:**
{content}

Generate the complete JSON rubric for indicators B1-B11:"""

    try:
        response = openai.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.3,
            max_tokens=4000,  # Increased for new format
        )
        
        text = response.choices[0].message.content
        if text is None:
            raise HTTPException(status_code=500, detail="No response from OpenAI API.")
        
        # Clean up the response to extract JSON
        text = text.strip()
        
        # Try to find JSON object with questions array
        import re
        json_match = re.search(r'\{[\s\S]*"questions"[\s\S]*\}', text)
        if json_match:
            rubric_json = json.loads(json_match.group(0))
        else:
            # Try to extract content between ```json blocks
            json_code_match = re.search(r'```json\s*(.*?)\s*```', text, re.DOTALL)
            if json_code_match:
                rubric_json = json.loads(json_code_match.group(1))
            else:
                # Try to parse the whole response
                try:
                    rubric_json = json.loads(text)
                except:
                    raise ValueError("Could not extract valid JSON from response")
        
        # Validate structure
        if "questions" not in rubric_json:
            raise ValueError("Response missing 'questions' array")
        
        questions = rubric_json["questions"]
        
        # Validate that we have all 11 indicators
        if len(questions) != 11:
            # If missing indicators, fill them with basic structure
            existing_orders = {q.get('order') for q in questions}
            for i in range(1, 12):
                if i not in existing_orders:
                    questions.append({
                        "prompt": f"B{i}: Indicator {i} - please refer to official rubric",
                        "order": i,
                        "options": [
                            {
                                "label": "Evidence present in lesson plan",
                                "value": "A",
                                "score_type": "yes",
                                "order": 1
                            },
                            {
                                "label": "Limited evidence in lesson plan",
                                "value": "B", 
                                "score_type": "partial",
                                "order": 2
                            },
                            {
                                "label": "No evidence in lesson plan",
                                "value": "C",
                                "score_type": "no",
                                "order": 3
                            }
                        ]
                    })
        
        # Sort questions by order and take only first 11
        questions = sorted(questions, key=lambda x: x.get('order', 0))[:11]
        rubric_json["questions"] = questions
        
        # Validate and return
        return SurveyRubric(**rubric_json)
        
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
            "sample_lesson": "/sample-lesson-plan",
            "rubric_from_string": "/rubric-from-string",
            "rubric_from_filepath": "/rubric-from-filepath"
        }
    }