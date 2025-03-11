import os
import re
import requests
import cv2
from pdf2image import convert_from_path
from flask import Flask, request, jsonify

app = Flask(__name__)

OCR_API_KEY = 'helloworld'  # استبدل بمفتاحك الحقيقي

# ---------------------- OCR Function ----------------------
def ocr_space_api(image_path):
    try:
        with open(image_path, 'rb') as image_file:
            response = requests.post(
                'https://api.ocr.space/parse/image',
                files={'file': image_file},
                data={'apikey': OCR_API_KEY, 'language': 'ara'},
                timeout=60
            )
            result = response.json()
            if 'ParsedResults' in result and result['ParsedResults']:
                return result['ParsedResults'][0]['ParsedText']
            else:
                return ""
    except Exception as e:
        print(f"❌ OCR Error: {e}")
        return ""

# ---------------------- Preprocessing ----------------------
def preprocess_image(image_path):
    try:
        image = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
        _, binary = cv2.threshold(image, 180, 255, cv2.THRESH_BINARY)
        blurred = cv2.GaussianBlur(binary, (5, 5), 0)
        processed_path = f"processed_{os.path.basename(image_path)}"
        cv2.imwrite(processed_path, blurred)
        return processed_path
    except Exception as e:
        print(f"❌ Preprocessing Error: {e}")
        return image_path

# ---------------------- Convert PDF to Image (Page 2 if exists) ----------------------
def pdf_to_image(pdf_path):
    try:
        images = convert_from_path(pdf_path, dpi=300)
        if len(images) >= 2:
            img = images[1]  # صفحة 2
            image_path = "page_2.png"
        else:
            img = images[0]  # صفحة 1 إذا ما في 2
            image_path = "page_1.png"
        img.save(image_path, "PNG")
        return image_path
    except Exception as e:
        print(f"❌ PDF to Image Error: {e}")
        return None

# ---------------------- Extract Data from Text ----------------------
def extract_data_from_text(text):
    text = re.sub(r'\s+', ' ', text).strip()
    extracted_data = {
        "Name": "غير متوفر",
        "ID No": "غير متوفر",
        "University No": "غير متوفر",
        "GPA": "غير متوفر",
        "Mobile No": "غير متوفر",
        "Major": "غير متوفر",
        "Duration": "غير متوفر",
        "Start Date": "غير متوفر",
        "End Date": "غير متوفر"
    }

    name_match = re.search(r"اسم[\s:\/-]*\S+\s+(\S+\s+\S+\s+\S+)", text)
    id_match = re.search(r"(1\d{9})", text)
    university_match = re.search(r"(4\d{8})", text)
    mobile_match = re.search(r"(05\d{8})", text)
    duration_match = re.search(r"مدة التدريب\s*\(.*?\)\s*(\d+)", text)
    start_date_match = re.search(r"(\d{4}/\d{2}/\d{2})", text)
    end_date_match = re.search(r"(\d{4}/\d{2}/\d{2})", text[start_date_match.end():]) if start_date_match else None

    extracted_data["Name"] = name_match.group(1).strip() if name_match else "غير متوفر"
    extracted_data["ID No"] = id_match.group(1).strip() if id_match else "غير متوفر"
    extracted_data["University No"] = university_match.group(1).strip() if university_match else "غير متوفر"
    extracted_data["Mobile No"] = mobile_match.group(1).strip() if mobile_match else "غير متوفر"
    extracted_data["Duration"] = duration_match.group(1).strip() if duration_match else "غير متوفر"
    extracted_data["Start Date"] = start_date_match.group(1).strip() if start_date_match else "غير متوفر"
    extracted_data["End Date"] = end_date_match.group(1).strip() if end_date_match else "غير متوفر"

    return extracted_data

# ---------------------- Process PDF ----------------------
def process_pdf(pdf_path):
    image_path = pdf_to_image(pdf_path)
    if not image_path:
        return {}

    processed_img_path = preprocess_image(image_path)
    extracted_text = ocr_space_api(processed_img_path)

    # حذف الصور بعد الاستخدام
    if os.path.exists(image_path):
        os.remove(image_path)
    if os.path.exists(processed_img_path):
        os.remove(processed_img_path)

    return extract_data_from_text(extracted_text)

# ---------------------- Flask API Endpoint ----------------------
@app.route('/api/analyze_pdf', methods=['POST'])
def analyze_pdf():
    data = request.json
    file_url = data.get('file_url')
    file_name = data.get('file_name', 'file.pdf')

    if not file_url:
        return jsonify({"error": "file_url is required"}), 400

    # تحميل الملف
    response = requests.get(file_url)
    pdf_path = f"/tmp/{file_name}"
    with open(pdf_path, 'wb') as f:
        f.write(response.content)

    # تحليل
    extracted_data = process_pdf(pdf_path)

    # حذف pdf
    if os.path.exists(pdf_path):
        os.remove(pdf_path)

    extracted_data["File Name"] = file_name  # إضافة اسم الملف
    return jsonify(extracted_data)

# ---------------------- Run Server ----------------------
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
