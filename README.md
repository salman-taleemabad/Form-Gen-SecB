# Lesson Fidelity Rubric Generator

This project generates lesson-specific fidelity rubrics using OpenAI's GPT models. It provides a web interface and API endpoints for generating rubrics from lesson plans.

---

## Table of Contents
- [Features](#features)
- [Setup](#setup)
- [Creating the .env File](#creating-the-env-file)
- [Running the Application](#running-the-application)
- [API Endpoints](#api-endpoints)
- [Web Interface](#web-interface)
- [Example Usage](#example-usage)
- [Troubleshooting](#troubleshooting)

---

## Features
- Generate lesson fidelity rubrics for indicators B1–B11
- Accept lesson plans as text or file upload
- Download rubric as CSV, Excel, or Word
- Example lesson plan included
- REST API for programmatic access

---

## Setup

1. **Clone the repository:**
   ```bash
   git clone <repo-url>
   cd Form-Generation
   ```

2. **Create a virtual environment (recommended):**
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

---

## Creating the .env File

1. In the `backend/` directory, create a file named `.env`:
   ```bash
   touch backend/.env
   ```
2. Add your OpenAI API key to the `.env` file:
   ```env
   OPENAI_API_KEY=sk-...
   ```
   Replace `sk-...` with your actual OpenAI API key.

---

## Running the Application

1. **Start the FastAPI server:**
   ```bash
   uvicorn backend.main:app --reload
   ```
   By default, the app will be available at [http://127.0.0.1:8000](http://127.0.0.1:8000)

2. **Access the web interface:**
   Open your browser and go to [http://127.0.0.1:8000](http://127.0.0.1:8000)

---

## API Endpoints

### 1. `POST /generate-rubric`
- **Description:** Generate a rubric from a lesson plan (text or file).
- **Form Data:**
  - `lesson_plan` (string, optional): The lesson plan text.
  - `file` (file, optional): Upload a `.txt` file containing the lesson plan.
  - `format` (string, required): Either `text` or `file`.
- **Returns:** JSON array of rubric rows.

### 2. `POST /rubric-from-string`
- **Description:** Generate a rubric from a lesson plan string (JSON body).
- **Body:**
  ```json
  { "lesson_plan": "..." }
  ```
- **Returns:** JSON array of rubric rows.

### 3. `POST /rubric-from-filepath`
- **Description:** Generate a rubric from a file path (JSON body, server-side file).
- **Body:**
  ```json
  { "file_path": "/path/to/lesson.txt" }
  ```
- **Returns:** JSON array of rubric rows.

### 4. `GET /sample-lesson-plan`
- **Description:** Get an example lesson plan and rubric format.
- **Returns:**
  ```json
  { "lesson_plan": "...", "rubric": [...] }
  ```

### 5. `GET /health`
- **Description:** Health check endpoint.
- **Returns:**
  ```json
  { "status": "healthy", ... }
  ```

### 6. `GET /`
- **Description:** Web interface (HTML page).

---

## Web Interface
- Paste a lesson plan or upload a `.txt` file.
- Click **Generate Rubric** to create a rubric for indicators B1–B11.
- Download the rubric as CSV, Excel, or Word.
- Use the **Example Lesson Plan** button to try the app without your own data.

---

## Example Usage

### Using `curl` to call the API:

**Text input:**
```bash
curl -X POST -F "lesson_plan=..." -F "format=text" http://127.0.0.1:8000/generate-rubric
```

**File upload:**
```bash
curl -X POST -F "file=@lesson.txt" -F "format=file" http://127.0.0.1:8000/generate-rubric
```

**JSON body:**
```bash
curl -X POST -H "Content-Type: application/json" -d '{"lesson_plan": "..."}' http://127.0.0.1:8000/rubric-from-string
```

---

## Troubleshooting
- Ensure your `.env` file is in the `backend/` directory and contains a valid OpenAI API key.
- If you see errors about missing keys, check your `.env` and restart the server.
- For CORS or browser issues, try a private/incognito window.
- For further help, check the code or open an issue.

---

## License
MIT 
 