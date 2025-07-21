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

# --- Improved System Prompt ---
SYSTEM_PROMPT = """You are an expert lesson fidelity rubric generator. Your job is to create a lesson-specific JSON rubric for indicators B1–B11 based ONLY on the provided lesson plan.

**CRITICAL INSTRUCTIONS:**
1. Use ONLY evidence and language explicitly present in the provided lesson plan
2. Do NOT generalize, infer, or add information not directly stated
3. Make descriptions specific to the actual lesson content, not generic
4. For each indicator, provide "Yes", "Partial", and "No" criteria that reflect:
   - YES: Complete fulfillment based on lesson plan evidence
   - PARTIAL: Incomplete or limited evidence in the lesson plan  
   - NO: Total absence of evidence in the lesson plan

**OFFICIAL INDICATORS B1-B11:**
B1: The teacher clearly states the lesson's objectives at the start verbally and in written form.
B2: The teacher uses either the resources outlined in the lesson plan or alternative resources facilitating the SLO.
B3: The teacher applies the suggested learning methodologies to facilitate effective lesson delivery.
B4: The teacher clearly relates classroom activities to the stated objectives.
B5: The teacher designs and delivers instruction that aligns with the cognitive level of the lesson's stated learning objective.
B6: The teacher effectively incorporates 21st century skills into the instructional process.
B7: The teacher connects the lesson's opening to students' prior knowledge through targeted questioning or an activity outlined in the lesson plan.
B8: The teacher makes connections in the lesson that relate to other content knowledge or students' daily lives.
B9: The teacher provides clear instructions and facilitates most of the students during Guided Practice (GP).
B10: The teacher gives clear instructions and monitors most of the students during Independent Practice (IP).
B11: The teacher follows the sequence of GRR Model (Gradual Release of Responsibility) throughout the lesson.

Output format: JSON array of objects with keys: code, indicator_description, yes, partial, no."""

# --- Single High-Quality Example ---
EXAMPLE_LESSON_PLAN = """Understanding Pronouns

Student Learning Objective
• Identify subject, object, and possessive pronouns in sentences.
• Write sentences using each type of pronoun correctly.

Summary
Today's lesson focuses on understanding pronouns, such as subject, object, and possessive pronouns.
The initial mind-mapping activity introduces critical thinking skills through visual connections.
Use textbook material on page 116 for guided exercises and discussions.
Engage students in pairs for collaborative practice and individual tasks for comprehension.
Conclude with 'Thumbs Up, Thumbs Down' to assess understanding of pronouns effectively.

Resources
Textbook page 116.

Opening
Say: Good morning, students! Today, we'll explore some special words we use every day in a fun way. Let's start with a quick activity!
Instruction: Ask students to raise their hands if they're ready to play a mind game.
Ask: Write the phrase 'I would…' on the board. (Ask students to complete the sentence.)
Ans: Possible answers: 'I would like to watch a movie,' 'I would eat my favourite food.'
Instruction: Invite a few students to share their ideas with the class.
Say: Wonderful! Did you notice how we used words like 'I,' 'you,' and 'my'? These are special words we use every day. Let's dive deeper into learning more about them!

Explanation
Instruction: Write 'Pronouns' on the board and underline it.
Instruction: Draw a simple mind map on the board connecting Pronouns to three branches: Subject, Object, and Possessive.
Say: This mind map shows how pronouns do different jobs. Let's understand these, one by one!
Instruction: Point to 'Subject' on the mind map and write examples: I, he, she, we, they, It.
Say: Subject pronouns tell us who is doing the action in a sentence. Examples: I play cricket. He draws well.
Ask: Who is doing the action in these sentences?
Ans: 'I' and 'He'
Instruction: Point to 'Object' on the mind map and write examples: me, her, him, us, them.
Say: Object pronouns tell us who is receiving the action. Example Context: Bilal and Sara went to a park. Bilal gave a ball to her.
Ask: Can anyone tell me what 'her' is doing here?
Ans: It shows who received the ball.
Instruction: Point to Possessive Pronouns on the mind map and write examples: mine, yours, his, hers, ours, theirs.
Say: Possessive pronouns show what belongs to someone. Examples: This pen is mine. That book is hers.
Ask: What does 'mine' show?
Ans: It shows the pen belongs to me.
Instruction: Encourage students to think of questions like Whose pen is this? or Who owns this book? to better understand possessive pronouns.
Say: Great work, everyone! Now let's practice using these pronouns in sentences!

Guided Practice
Say: Now that we know about Subject Pronouns, Object Pronouns, and Possessive Pronouns, let's use them to create sentences!
Instruction: Pair Work: Ask students to pair up with the student sitting next to them. Each pair will write three sentences—one for each type of pronoun (subject, object, possessive) in their notebook.
Ans: Sample Sentences: We are going to the park. (Subject Pronoun). He gave the ball to us. (Object Pronoun). The ball is ours. (Possessive Pronoun)
Instruction: Once done, call each pair to share their sentences with the class Write a few student-generated sentences on the board for discussion.
Instruction: Walk around to guide and check if pairs are using pronouns correctly. Provide constructive feedback after pairs share their sentences.
Say: Great teamwork! You've learned how to use all three types of pronouns in sentences. Keep practising, and you'll get even better!

Independent practice
Say: Now that you have practiced with a partner, let's put your skills to the test on your own.
Instruction: Turn to page 116 in your textbook.
Instruction: Complete Exercise ii where you need to write two subject, two object, and two possessive pronouns each with sentences in your notebooks.
Ask: If you need help, what sentence could you try first?
Ans: I could start with 'I have a cat.'
Instruction: Remind students that they can look back at examples they created with their partners earlier.
Instruction: Tell students to raise their hand if they finish early and check with you for accuracy.
Instruction: Walk around the class, providing help as needed and checking sentences.
Instruction: Encourage students to refine sentences or try another if they seem confident.
Instruction: Reassure students that this is their chance to show how much they've learned today.

Conclusion
Instruction: Let's wrap up our lesson with a quick game.
Ask: Thumbs up if this is true: 'A pronoun never acts as a subject in a sentence.'
Ans: Thumbs down, because pronouns can act as subjects.
Ask: Thumbs up if this is true: 'Possessive pronouns show what belongs to someone.'
Ans: Thumbs up, because possessive pronouns do show ownership.
Instruction: Great job! Remember to think about how pronouns work with the sentences you create.

Homework
Observe your surroundings and identify pronouns you hear; try to write three sentences at home. Complete the missing letters on page 115 under 'Learing to Spell' in the textbook."""

EXAMPLE_RUBRIC = [
    {
        "code": "B1",
        "indicator_description": "The teacher clearly states the lesson's objectives at the start verbally and in written form.",
        "yes": "The teacher verbally states the written objectives: 'Identify subject, object, and possessive pronouns in sentences and write sentences using each type of pronoun correctly.'",
        "partial": "The teacher either states the objectives verbally OR they are written in the plan, but not both clearly communicated to students.",
        "no": "The teacher neither verbally states nor references the written objectives at the lesson start."
    },
    {
        "code": "B2", 
        "indicator_description": "The teacher uses either the resources outlined in the lesson plan or alternative resources facilitating the SLO.",
        "yes": "The teacher uses textbook page 116 as specified, plus board for mind mapping and pronoun examples as outlined in the plan.",
        "partial": "The teacher uses textbook page 116 but omits the mind mapping or board work described in the plan.",
        "no": "The teacher does not use textbook page 116 or any alternative resources supporting pronoun identification and sentence writing."
    },
    {
        "code": "B3",
        "indicator_description": "The teacher applies the suggested learning methodologies to facilitate effective lesson delivery.", 
        "yes": "The teacher implements mind-mapping, pair work for sentence creation, individual textbook exercises, and 'Thumbs Up/Down' assessment as described.",
        "partial": "The teacher uses some methods (e.g., mind-mapping and pair work) but omits others like individual practice or thumbs assessment.",
        "no": "The teacher does not apply the planned methodologies; lesson lacks mind-mapping, collaborative work, or structured assessment."
    },
    {
        "code": "B4",
        "indicator_description": "The teacher clearly relates classroom activities to the stated objectives.",
        "yes": "All activities (mind-mapping pronoun types, pair sentence writing, individual textbook exercises) directly support identifying and using pronouns in sentences.",
        "partial": "Some activities relate to pronoun identification but the connection to sentence writing objectives is unclear or incomplete.",
        "no": "Activities do not clearly connect to the objectives of identifying pronouns or writing sentences with different pronoun types."
    },
    {
        "code": "B5",
        "indicator_description": "The teacher designs and delivers instruction that aligns with the cognitive level of the lesson's stated learning objective.",
        "yes": "Visual mind-mapping, concrete examples ('This pen is mine'), and scaffolded practice align with elementary students' need for concrete learning about pronouns.",
        "partial": "Some activities are age-appropriate (examples) but others lack sufficient scaffolding or visual support for elementary pronoun learning.",
        "no": "Instruction is too abstract or advanced for elementary students learning basic pronoun identification and usage."
    },
    {
        "code": "B6",
        "indicator_description": "The teacher effectively incorporates 21st century skills into the instructional process.",
        "yes": "Lesson integrates collaboration (pair sentence writing), critical thinking (mind-mapping pronoun categories), and communication (class sharing and discussion).",
        "partial": "Lesson includes collaboration through pair work but limited evidence of critical thinking or structured communication skills.",
        "no": "No evidence of collaboration, critical thinking, or communication skills; lesson is teacher-directed without student interaction."
    },
    {
        "code": "B7",
        "indicator_description": "The teacher connects the lesson's opening to students' prior knowledge through targeted questioning or an activity outlined in the lesson plan.",
        "yes": "The 'I would...' completion activity and follow-up questioning ('Did you notice how we used words like I, you, my?') connects to students' daily pronoun use.",
        "partial": "The opening activity occurs but the connection to students' prior knowledge of pronouns is weak or unclear.",
        "no": "No attempt to connect the lesson opening to students' existing knowledge of pronouns or their daily language use."
    },
    {
        "code": "B8",
        "indicator_description": "The teacher makes connections in the lesson that relate to other content knowledge or students' daily lives.",
        "yes": "Examples like 'This pen is mine,' 'That book is hers,' and encouraging students to find pronouns in their surroundings connect to daily life and school materials.",
        "partial": "Some real-life examples are provided but connections to students' daily experiences are limited or superficial.",
        "no": "No connections made between pronouns and students' daily life, school materials, or other subject areas."
    },
    {
        "code": "B9",
        "indicator_description": "The teacher provides clear instructions and facilitates most of the students during Guided Practice (GP).",
        "yes": "Teacher gives specific pair work instructions (write three sentences, one for each pronoun type), walks around to guide and check, facilitates sharing with feedback.",
        "partial": "Instructions for pair work are given but teacher provides limited guidance or facilitation during the guided practice.",
        "no": "No clear guided practice instructions provided, or teacher does not facilitate or support students during pair work."
    },
    {
        "code": "B10", 
        "indicator_description": "The teacher gives clear instructions and monitors most of the students during Independent Practice (IP).",
        "yes": "Teacher directs students to page 116 Exercise ii, explains the task (write sentences with different pronouns), walks around providing help and checking accuracy.",
        "partial": "Clear instructions given for textbook exercise but limited evidence of teacher monitoring or supporting individual students.",
        "no": "No independent practice task assigned or teacher provides no monitoring or support during individual work."
    },
    {
        "code": "B11",
        "indicator_description": "The teacher follows the sequence of GRR Model (Gradual Release of Responsibility) throughout the lesson.",
        "yes": "Clear 'I Do' (teacher explains and models pronouns with mind map), 'We Do' (pair sentence writing), and 'You Do' (individual textbook exercises) sequence.",
        "partial": "Some elements of GRR present but sequence is unclear or one component (like modeling or independent practice) is weak.",
        "no": "No evidence of GRR model; lesson lacks structured progression from teacher modeling to student independence."
    }
]

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

    # Improved prompt structure with clear separation
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
            max_tokens=2500,  # Increased for complete rubrics
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
            max_tokens=2500,
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