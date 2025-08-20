from fastapi import FastAPI, WebSocket, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
import openai, os, pdfplumber, re, json, tempfile
from typing import List
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Frame, PageTemplate
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_LEFT


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILES_DIR = os.path.join(BASE_DIR, 'data-files')

# Set up OpenAI API key from environment (do not hardcode secrets)
openai.api_key = os.getenv('OPENAI_API_KEY', '')
client = openai.OpenAI(api_key=openai.api_key)

app = FastAPI()

# Allow CORS
origins = [
    "http://localhost",
    "http://localhost:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def chatbot_response(query):
    try:
        response = client.completions.create(
            model="gpt-3.5-turbo-instruct",
            prompt=query,
            max_tokens=100
        )
        return response.choices[0].text.strip()
    except Exception as e:
        return f"Error: {str(e)}"

# PDF content extraction
def read_pdf_contents(pdf_path):
    with pdfplumber.open(pdf_path) as pdf:
        content = []
        for page in pdf.pages:
            text = page.extract_text()
            content.append(text)
    return content

def extract_patient_info(content):
    patient_info = {}
    for page_text in content:
        name_match = re.search(r'Patient Name\s*:\s*([\w\s.]+)', page_text)
        age_match = re.search(r'Age/Gender\s*:\s*([\d\w\s/]+)', page_text)
        weight_match = re.search(r'Weight\s*:\s*([\d.]+)', page_text)
        height_match = re.search(r'Height\s*:\s*([\d.]+)', page_text)
        if name_match and age_match:
            patient_info['name'] = name_match.group(1).strip()
            patient_info['age'] = age_match.group(1).strip()
            patient_info['weight'] = weight_match.group(1).strip() if weight_match else "Not found"
            patient_info['height'] = height_match.group(1).strip() if height_match else "Not found"
            break
    return patient_info

def extract_test_results(content):
    test_results = {}
    for page_text in content:
        lines = page_text.split('\n')
        for line in lines:
            if re.match(r'\w[\w\s,]*\s+\d+\.?\d*', line):
                match = re.match(r'(\w[\w\s,]*)\s+(\d+\.?\d*)', line)
                if match:
                    test_name = match.group(1).strip()
                    test_value = match.group(2).strip()
                    if not re.search(r'Page \d+ of|\bAs per\b|EXCELLENT CONTROL|FAIR TO GOOD CONTROL|UNSATISFACTORY CONTROL|Control by American Diabetes Association guidelines', test_name):
                        test_results[test_name] = test_value
    return test_results

def analyze_and_prescribe(report, api_key):
    client = openai.OpenAI(api_key=api_key)

    # Diagnostic suggestions
    response = client.completions.create(
        model="gpt-3.5-turbo-instruct",
        prompt=f"Analyze the following pathology report and provide diagnostic suggestions and identify any patterns or correlations relevant to diabetic patients. Ensure the response is well-structured and properly formatted. End with a clear conclusion.\n\nPathology Report:\n{report}\n\nDiagnostic Suggestions:",
        max_tokens=300
    )
    analysis = response.choices[0].text.strip()
    
    # Recommendations
    response = client.completions.create(
        model="gpt-3.5-turbo-instruct",
        prompt=f"Based on the following analysis, provide detailed recommendations for lifestyle changes and further medical actions in a well-structured and properly formatted manner. End with a clear conclusion.\n\nAnalysis:\n{analysis}\n\nRecommendations:",
        max_tokens=300
    )
    recommendations = response.choices[0].text.strip()
    
    # Medications
    response = client.completions.create(
        model="gpt-3.5-turbo-instruct",
        prompt=f"Based on the following analysis, provide a list of 10 medications for the identified disease in a well-structured, bullet-point format. End with a clear conclusion.\n\nAnalysis:\n{analysis}\n\nMedications:",
        max_tokens=300
    )
    medications = response.choices[0].text.strip()
    
    return analysis, recommendations, medications

def generate_prescription_pdf(patient_info, analysis, recommendations, medications, file_name, bg_image_path):
    doc = SimpleDocTemplate(file_name, pagesize=letter)
    content = []

    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name='Justify', alignment=TA_LEFT))
    styles.add(ParagraphStyle(name='Bold', fontName='Helvetica-Bold', alignment=TA_LEFT))

    # Prescription Title
    content.append(Paragraph("Prescription", styles['Title']))
    content.append(Spacer(1, 12))

    # Patient Info
    patient_name = patient_info.get('name', 'Not found')
    patient_age = patient_info.get('age', 'Not found')
    patient_height = patient_info.get('height', 'Not found')
    patient_weight = patient_info.get('weight', 'Not found')
    content.append(Paragraph(f"Patient: {patient_name}", styles['Normal']))
    content.append(Paragraph(f"Age: {patient_age}", styles['Normal']))
    content.append(Paragraph(f"Height: {patient_height}", styles['Normal']))
    content.append(Paragraph(f"Weight: {patient_weight}", styles['Normal']))
    content.append(Spacer(1, 12))

    # Analysis
    content.append(Paragraph("Diagnosis:", styles['Heading2']))
    content.append(Spacer(1, 6))
    content.append(Paragraph(analysis.replace('\n', '<br/>'), styles['Justify']))
    content.append(Spacer(1, 12))

    # Recommendations
    content.append(Paragraph("Recommendations:", styles['Heading2']))
    content.append(Spacer(1, 6))
    content.append(Paragraph(recommendations.replace('\n', '<br/>'), styles['Justify']))
    content.append(Spacer(1, 12))

    # Medications
    content.append(Paragraph("Medications:", styles['Heading2']))
    content.append(Spacer(1, 6))
    content.append(Paragraph(medications.replace('\n', '<br/>'), styles['Justify']))

    # Add background image to every page
    def add_background(canvas, doc):
        canvas.saveState()
        width, height = letter
        image_width = width
        image_height = height
        if bg_image_path:
            img = Image(bg_image_path, width=image_width, height=image_height)
            img.drawOn(canvas, 0, 0)
        canvas.restoreState()

    # Create a page template with background
    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id='normal')
    doc.addPageTemplates([PageTemplate(id='Later', frames=frame, onPage=add_background)])

    doc.build(content)

@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    if not file:
        raise HTTPException(status_code=400, detail="No file uploaded")  

    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_file:
        temp_file_path = temp_file.name
        file_contents = await file.read()
        temp_file.write(file_contents)

    pdf_contents = read_pdf_contents(temp_file_path)
    patient_info = extract_patient_info(pdf_contents)
    test_results = extract_test_results(pdf_contents)

    initial_test_names = ["HAEMOGLOBIN", "PCV", "RBC COUNT", "GLUCOSE, FASTING , NAF PLASMA", "HBA1C, GLYCATED HEMOGLOBIN", "CREATININE , SERUM"]
    initial_report = {test: test_results[test] for test in initial_test_names if test in test_results}

    report = f"Patient Name: {patient_info.get('name', 'Not found')}\n"
    report += f"Age: {patient_info.get('age', 'Not found')}\n"
    report += f"Height: {patient_info.get('height', 'Not found')}\n"
    report += f"Weight: {patient_info.get('weight', 'Not found')}\n\n"
    report += "Test Results:\n"
    for test_name, result in initial_report.items():
        report += f"{test_name}: {result}\n"

    analysis, recommendations, medications = analyze_and_prescribe(report, openai.api_key)
    
    response_data = {
        "Patient Information": patient_info,
        "Lab Test Results": test_results,
        "Analysis and Recommendation": {
            "Analysis": analysis,
            "Recommendations": recommendations,
            "Medications": medications
        },
        "new_updated_Analysis_and_Recommendation": {},
        "Chat History": []
    }

    with open(os.path.join(DATA_FILES_DIR, 'results.json'), 'w') as f:
        json.dump(response_data, f, indent=4)

    os.remove(temp_file_path)
    
    return {"data": response_data}

@app.get("/results")
async def get_results():
    with open(os.path.join(DATA_FILES_DIR, 'results.json'), 'r') as f:
        data = json.load(f)
    return data

@app.post("/update_profile")
async def update_profile(profile_data: dict):
    try:
        with open(os.path.join(DATA_FILES_DIR, 'results.json'), 'r+') as f:
            data = json.load(f)
            data['Patient Information'].update(profile_data)
            f.seek(0)
            json.dump(data, f, indent=4)
            f.truncate()
        return {"message": "Profile updated successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
@app.post("/update_analysis")
async def update_analysis(selected_tests: List[str]):
    with open(os.path.join(DATA_FILES_DIR, 'results.json'), 'r') as f:
        data = json.load(f)

    test_results = data["Lab Test Results"]
    selected_tests_dict = {test: test_results[test] for test in selected_tests if test in test_results}

    report = f"Patient Name: {data['Patient Information'].get('name', 'Not found')}\n"
    report += f"Age: {data['Patient Information'].get('age', 'Not found')}\n"
    report += f"Height: {data['Patient Information'].get('height', 'Not found')}\n"
    report += f"Weight: {data['Patient Information'].get('weight', 'Not found')}\n\n"
    report += "Test Results:\n"
    for test_name, result in {**test_results, **selected_tests_dict}.items():
        report += f"{test_name}: {result}\n"

    analysis, recommendations, medications = analyze_and_prescribe(report, openai.api_key)

    data["new_updated_Analysis_and_Recommendation"] = {
        "Analysis": analysis,
        "Recommendations": recommendations,
        "Medications": medications
    }

    with open(os.path.join(DATA_FILES_DIR, 'results.json'), 'w') as f:
        json.dump(data, f, indent=4)

    return {"data": data["new_updated_Analysis_and_Recommendation"]}


@app.post("/generate_prescription")
async def generate_prescription(isUpdate: bool = False):
    with open(os.path.join(DATA_FILES_DIR, 'results.json'), 'r') as f:
        data = json.load(f)

    patient_info = data["Patient Information"]
    if isUpdate:
        analysis_data = data["new_updated_Analysis_and_Recommendation"]
    else:
        analysis_data = data["Analysis and Recommendation"]
    
    if not analysis_data:
        raise HTTPException(status_code=400, detail="Analysis data not found")

    analysis = analysis_data.get("Analysis", "Analysis not found")
    recommendations = analysis_data.get("Recommendations", "Recommendations not found")
    medications = analysis_data.get("Medications", "Medications not found")
    
    file_name = os.path.join(BASE_DIR,f"./Output-files/{patient_info.get('name', 'Patient').replace(' ', '_')}_prescription.pdf")
    bg_image_path = os.path.join(BASE_DIR, 'Group-1.png')
    generate_prescription_pdf(patient_info, analysis, recommendations, medications, file_name, bg_image_path)

    return {"file_path": file_name}

@app.get("/download")
async def download_prescription(file_path: str):
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(file_path, filename=os.path.basename(file_path))

# WebSocket endpoint
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    while True:
        try:
            data = await websocket.receive_text()
            response = chatbot_response(data)
            
            # Record chat history
            with open(os.path.join(DATA_FILES_DIR, 'results.json'), 'r+') as f:
                results_data = json.load(f)
                chat_history = results_data.get("Chat History", [])
                chat_history.append({"user": data, "bot": response})
                results_data["Chat History"] = chat_history
                f.seek(0)
                json.dump(results_data, f, indent=4)
                f.truncate()
            
            await websocket.send_text(response)
        except Exception as e:
            await websocket.send_text(f"Error: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
