import os
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Request, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from typing import List, Optional
from dotenv import load_dotenv
import json
from pathlib import Path
from backend.genai_service import GenAIService
from backend.prompts import EXAMPLE_LESSON_PLAN, EXAMPLE_RUBRIC

load_dotenv()

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

# Models for survey format
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

# --- Internal helper for rubric generation using new approach ---
async def _generate_rubric_from_content(content: str):
    """
    Generate rubric using the new single prompt approach (matching teammate's method)
    """
    try:
        print(f"🔍 DEBUG: Starting rubric generation for content length: {len(content)}")
        print(f"🔍 DEBUG: Content preview: {content[:200]}...")
        
        # Use the new GenAIService with single prompt approach
        print("🔍 DEBUG: Calling GenAIService.generate_rubric_from_lesson_plan...")
        response_content, tokens_used = GenAIService.generate_rubric_from_lesson_plan(
            lesson_plan=content
        )
        
        print(f"🔍 DEBUG: GenAIService returned response type: {type(response_content)}")
        print(f"🔍 DEBUG: Response content keys: {list(response_content.keys()) if isinstance(response_content, dict) else 'Not a dict'}")
        print(f"🔍 DEBUG: Tokens used: {tokens_used}")
        
        # Validate structure
        if "questions" not in response_content:
            print(f"❌ DEBUG: Response missing 'questions' array. Full response: {response_content}")
            raise ValueError("Response missing 'questions' array")
        
        questions = response_content["questions"]
        print(f"🔍 DEBUG: Found {len(questions)} questions in response")
        
        # Validate that we have all 11 indicators
        if len(questions) != 11:
            print(f"⚠️ DEBUG: Expected 11 questions, got {len(questions)}")
            # If missing indicators, fill them with basic structure
            existing_orders = {q.get('order') for q in questions}
            for i in range(1, 12):
                if i not in existing_orders:
                    print(f"🔍 DEBUG: Adding missing question B{i}")
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
        response_content["questions"] = questions
        
        print(f"🔍 DEBUG: Final questions count: {len(questions)}")
        print(f"🔍 DEBUG: First question preview: {questions[0] if questions else 'No questions'}")
        
        # Validate and return
        print("🔍 DEBUG: Creating SurveyRubric object...")
        result = SurveyRubric(**response_content)
        print(f"✅ DEBUG: Successfully created rubric with {len(result.questions)} questions")
        return result
        
    except Exception as e:
        print(f"❌ DEBUG: Error in _generate_rubric_from_content: {str(e)}")
        print(f"❌ DEBUG: Error type: {type(e)}")
        import traceback
        print(f"❌ DEBUG: Full traceback: {traceback.format_exc()}")
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
        "message": "Lesson Fidelity Rubric Generator (New Single Prompt Approach) is running",
        "timestamp": "2024-01-01T00:00:00Z",
        "version": "2.0.0",
        "endpoints": {
            "health": "/health",
            "home": "/",
            "generate_rubric": "/generate-rubric",
            "sample_lesson": "/sample-lesson-plan",
            "rubric_from_string": "/rubric-from-string",
            "rubric_from_filepath": "/rubric-from-filepath"
        }
    } 