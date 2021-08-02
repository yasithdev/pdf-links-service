import hashlib
import io
import json
import os

import requests
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
  return render_template("urls.html", filename=fp, urls=urls)


@app.route("/robustify", methods=['POST'])
def robustify():
  uris = request.get_json()

  def generate():
    for uri in uris:
      uri = uri.strip()
      res = requests.get(f"http://robustlinks.mementoweb.org/api/", {"url": uri})
      try:
        res_json = res.json()
        if 'robust_links_html' in res_json:
          yield json.dumps({
            "ok": True,
            "uri": uri,
            "href_uri_r": res_json['robust_links_html']['original_url_as_href'],
            "href_uri_m": res_json['robust_links_html']['memento_url_as_href'],
          }) + "\n"
        elif 'friendly error' in res_json:
          yield json.dumps({
            "ok": False,
            "uri": uri,
            "error": res_json['friendly error'].strip()
          }) + "\n"
      except json.JSONDecodeError:
        yield json.dumps({
          "ok": False,
          "uri": uri,
          "error": f"Did not receive JSON output for URI {uri}"
        }) + "\n"

  return app.response_class(generate(), content_type='application/octet-stream')


@app.route("/ldn", methods=['POST'])
def send_ldn():
  # get JSON payload
  payload = request.get_json()
  to: str = payload['to']
  message = payload['message']
  #
  link_header = request.headers.get("Link")


@app.route("/", methods=['GET'])
def main_page():
  return render_template("index.html")
