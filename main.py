
from flask import Flask, request, render_template_string, send_file
from PIL import Image, ImageDraw, ImageFont
import easyocr
import openai
import os
import uuid

app = Flask(__name__)
UPLOAD_FOLDER = "uploads"
TRANSLATED_FOLDER = "translated"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(TRANSLATED_FOLDER, exist_ok=True)

openai.api_key = os.getenv("OPENAI_API_KEY")
reader = easyocr.Reader(['en', 'ja', 'ko', 'zh', 'fr', 'es', 'de', 'it'])

TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
  <title>ComicGPT Translator</title>
  <style>
    body { font-family: sans-serif; background: #121212; color: white; margin: 0; padding: 2rem; }
    h1 { text-align: center; }
    form { text-align: center; margin-bottom: 2rem; }
    input, button { padding: 0.5rem; font-size: 1rem; }
    .image-container { text-align: center; margin-top: 1rem; }
    img { max-width: 80vw; height: auto; margin: 1rem 0; border-radius: 8px; }
    a { color: #9cf; display: block; margin-bottom: 2rem; }
  </style>
</head>
<body>
  <h1>ComicGPT Translator</h1>
  <form method="POST" action="/translate" enctype="multipart/form-data">
    <label>Select comic images:</label><br><br>
    <input type="file" name="images" multiple accept="image/png,image/jpeg"><br><br>
    <button type="submit">Translate to English</button>
  </form>
  {% if files %}
    <div class="image-container">
      <h2>Translated Images:</h2>
      {% for file in files %}
        <img src="/translated/{{ file }}">
        <a href="/translated/{{ file }}" download>Download {{ file }}</a>
      {% endfor %}
    </div>
  {% endif %}
</body>
</html>
'''

def translate_with_gpt(text):
    try:
        response = openai.ChatCompletion.create(
            model="gpt-4-1106-preview",
            messages=[
                {"role": "system", "content": "You are a professional Japanese-English manga translator. Translate faithfully."},
                {"role": "user", "content": f"Translate this manga/dialogue text to English: '{text}'"}
            ],
            temperature=0.5
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"[Error] {text}"

def process_image(image_path):
    image = Image.open(image_path).convert("RGB")
    draw = ImageDraw.Draw(image)
    font = ImageFont.load_default()
    results = reader.readtext(image_path)

    for (bbox, text, prob) in results:
        if prob < 0.5 or len(text.strip()) < 1:
            continue
        translated = translate_with_gpt(text.strip())
        top_left = tuple(map(int, bbox[0]))
        bottom_right = tuple(map(int, bbox[2]))
        draw.rectangle([top_left, bottom_right], fill="black")
        draw.text(top_left, translated, fill="white", font=font)

    output_path = os.path.join(TRANSLATED_FOLDER, f"{uuid.uuid4().hex}.jpg")
    image.save(output_path)
    return os.path.basename(output_path)

@app.route('/', methods=['GET'])
def index():
    return render_template_string(TEMPLATE)

@app.route('/translate', methods=['POST'])
def translate():
    uploaded_files = request.files.getlist("images")
    translated_files = []
    for file in uploaded_files:
        filename = f"{uuid.uuid4().hex}.jpg"
        path = os.path.join(UPLOAD_FOLDER, filename)
        file.save(path)
        translated_name = process_image(path)
        translated_files.append(translated_name)
    return render_template_string(TEMPLATE, files=translated_files)

@app.route('/translated/<filename>')
def get_image(filename):
    return send_file(os.path.join(TRANSLATED_FOLDER, filename), mimetype='image/jpeg')

if __name__ == '__main__':
    app.run(debug=True)
