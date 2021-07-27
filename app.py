import hashlib
import io
import os

from flask import Flask, render_template, request, redirect

from extractor import Extractor

UPLOAD_FOLDER = './uploads'

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

extractor = Extractor()


@app.route('/upload', methods=['POST'])
def upload_pdf():
  # sanity check
  if 'file' not in request.files:
    return redirect('/')
  # get file object
  file = request.files['file']
  # copy PDF into in-memory buffer
  data = io.BytesIO()
  data.write(file.stream.read())
  # seek to beginning of buffer
  data.seek(0)
  # calculate MD5 hash (which will be used as filename)
  out_basename = hashlib.md5(data.read()).hexdigest() + ".pdf"
  out_path = os.path.join(app.config['UPLOAD_FOLDER'], out_basename)
  # seek to beginning of buffer
  data.seek(0)
  # write buffer to file
  with open(out_path, "wb") as f:
    f.write(data.read())
  # redirect to URL extraction page
  return redirect(f'/extract/{out_basename}')


@app.route("/extract/<fp>", methods=['GET'])
def extract_links(fp: str):
  urls = extractor.extract_urls(os.path.join(app.config['UPLOAD_FOLDER'], fp))
  return render_template("urls.html", urls=urls)


@app.route("/")
def main_page():
  return render_template("index.html")
