import hashlib
import io
import json
import os

import flask
import requests
from flask import Flask, render_template, request, redirect, send_file

from extractor import Extractor

app = Flask(__name__)
app.config['UPLOADS_FOLDER'] = './pdfs'
app.config['MAPPING_FOLDER'] = './mappings'
extractor = Extractor()


@app.route('/pdfs', methods=['POST'])
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
  out_basename = hashlib.md5(data.read()).hexdigest()
  out_path = os.path.join(app.config['UPLOADS_FOLDER'], out_basename + ".pdf")
  # seek to beginning of buffer
  data.seek(0)
  # write buffer to file
  with open(out_path, "wb") as f:
    f.write(data.read())
  # redirect to URL extraction page
  return redirect(f'/links/{out_basename}')


@app.route("/pdfs/<pdf_name>", methods=['GET'])
def get_pdf(pdf_name: str):
  return send_file(os.path.join(app.config['UPLOADS_FOLDER'], pdf_name + ".pdf"))


@app.route("/links/<pdf_name>", methods=['GET'])
def get_extract_links_page(pdf_name: str):
  urls = extractor.extract_urls(os.path.join(app.config['UPLOADS_FOLDER'], pdf_name + ".pdf"))
  return render_template("links.html", filename=pdf_name, urls=urls)


def save_mappings(mappings: dict, pdf_name: str):
  # write mappings to file
  with open(os.path.join(app.config['MAPPING_FOLDER'], pdf_name + "pdf.json"), "w") as f:
    json.dump(mappings, f)


@app.route("/mappings/<pdf_name>", methods=['GET'])
def get_mappings(pdf_name: str):
  return send_file(os.path.join(app.config['MAPPING_FOLDER'], pdf_name + ".pdf.json"))


@app.route("/robustify", methods=['POST'])
def robustify():
  req_json = request.get_json()
  filename = req_json['filename']
  uris = req_json['uris']

  def generate():
    mappings = {}
    # robustify the given uris
    for uri in uris:
      uri = uri.strip()
      res = requests.get(f"http://robustlinks.mementoweb.org/api/", {"url": uri})
      try:
        res_json = res.json()
        if 'robust_links_html' in res_json:
          payload = {
            "ok": True,
            "uri": uri,
            "href_uri_r": res_json['robust_links_html']['original_url_as_href'],
            "href_uri_m": res_json['robust_links_html']['memento_url_as_href'],
          }
        elif 'friendly error' in res_json:
          payload = {
            "ok": False,
            "uri": uri,
            "error": res_json['friendly error'].strip()
          }
        else:
          payload = {
            "ok": False,
            "uri": uri,
            "error": "Unknown Error from Robust Links API"
          }
      except json.JSONDecodeError:
        payload = {
          "ok": False,
          "uri": uri,
          "error": f"Error decoding response (JSON) from Robust Links API for URI {uri}"
        }
      mappings[uri] = payload
      # stream progress for each uri
      yield json.dumps(payload) + "\n"
    # save mappings into file
    save_mappings(mappings, filename)

  return app.response_class(generate(), content_type='application/octet-stream')


@app.route("/notify", methods=['POST'])
def send_ldn():
  # get JSON payload
  payload = request.get_json()
  to: str = payload['to']
  message = payload['message']
  #
  res = requests.head(to)
  ldn_inbox_rel = "http://www.w3.org/ns/ldp#inbox"
  if ldn_inbox_rel not in res.links:
    return flask.jsonify({"ok": False, "error": f"The URL {to} does not reference an LDN Inbox"})
  # Get LDN inbox URL
  ldn_inbox_url = res.links[ldn_inbox_rel]['url']
  return flask.jsonify({"ok": True, "ldn_inbox_url": ldn_inbox_url})
  # Send LDN


@app.route("/", methods=['GET'])
def main_page():
  return render_template("index.html")
