import datetime
import hashlib
import io
import json
import os
import platform

import flask
import requests

from .extractor import Extractor

app = flask.Flask(__name__)
app.config['UPLOADS_FOLDER'] = './pdfs'
app.config['MAPPING_FOLDER'] = './mappings'
app.config['DOCS_FOLDER'] = '../docs/_build/html'
extractor = Extractor()

ERR_MSG_TITLE = "Error!"
ERR_MSG_PDF_NOT_FOUND = "The requested PDF file was not found"
ERR_MSG_PDF_META_NOT_FOUND = "The metadata for the requested PDF file was not found. Please try uploading the PDF again to generate metadata."
ERR_MSG_MAPPING_NOT_FOUND = "The requested mappings do not exist"
ERR_MSG_MISSING_PARAM_FILE = "Missing required parameter 'file'"
ERR_MSG_ONLY_PDF_ALLOWED = "You are only allowed to upload PDF files"


def __make_error_response(status: int, message: str):
  """
  Generate an error response.

  If the request accepts HTML, the error will be rendered as a HTML page.
  Instead, if the request accepts JSON, the error will be rendered as JSON.
  If neither, the error will be rendered as plain text.

  :param status: HTTP status code
  :param message: Message included in the error response
  :return: An HTTP response with the given status and message

  """

  mimes = flask.request.accept_mimetypes
  if mimes.accept_html:
    body = flask.render_template('error.html', title=ERR_MSG_TITLE, message=message)
  elif mimes.accept_json:
    body = {"timestamp": datetime.datetime.utcnow().isoformat(), "error": message}
  else:
    body = message
  return flask.make_response(body, status)


@app.route('/pdfs', methods=['POST'])
def upload_pdf():
  """
  Route to upload a PDF file.

  This function intercepts ``POST`` requests to ``/pdfs``.
  It expects the request body to contain form data, with an encoding type of ``multipart/form-data``.
  This form data should reference the PDF file as ``<input type="file" name="file">``.

  Upon success, this function will return a ``302 Found`` that redirects to ``/links/<pdf_hash>``.
  Here, ``pdf_hash`` is the MD5 hash of the uploaded PDF (calculated server-side).

  Upon error, this function with return a ``400 Bad Request`` response with information about the error.

  :return: An HTTP Response

  """

  # assert that request contains a file
  if 'file' not in flask.request.files:
    return flask.abort(__make_error_response(400, ERR_MSG_MISSING_PARAM_FILE))
  # get file from the request
  file = flask.request.files['file']
  orig_filename = file.filename
  # ensure that the file is a pdf
  if file.mimetype != 'application/pdf':
    return flask.abort(__make_error_response(400, ERR_MSG_ONLY_PDF_ALLOWED))
  # copy the PDF into an in-memory buffer
  data = io.BytesIO()
  data.write(file.stream.read())
  # seek to the beginning of the buffer
  data.seek(0)
  # calculate MD5 hash (which will be used as filename)
  out_basename = hashlib.md5(data.read()).hexdigest()
  out_path = os.path.join(app.config['UPLOADS_FOLDER'], out_basename)
  # seek to the beginning of the buffer
  data.seek(0)
  # write the buffer to file
  with open(out_path + ".pdf", "wb") as f:
    f.write(data.read())
  with open(out_path + ".pdf.txt", "w") as f:
    f.write(orig_filename)
  # redirect to URL extraction page
  return flask.redirect(f'/links/{out_basename}')


@app.route("/pdfs/<pdf_hash>", methods=['GET'])
def get_pdf(pdf_hash: str):
  """
  Route to get a PDF file.

  This function intercepts ``GET`` requests to ``/pdfs/<pdf_hash>``.
  It looks for a PDF that matches the given hash.
  If found, it returns a ``200 OK`` response with the PDF.
  If not, it returns a ``404 Not Found`` response.

  :param pdf_hash: MD5 hash of an uploaded PDF
  :return: An HTTP Response

  """

  # assert that PDF exists
  pdf_path = os.path.join(app.config['UPLOADS_FOLDER'], pdf_hash + ".pdf")
  if not os.path.exists(pdf_path):
    flask.abort(__make_error_response(404, ERR_MSG_PDF_NOT_FOUND))
  # send file
  return flask.send_file(pdf_path)


@app.route("/links/<pdf_hash>", methods=['GET'])
def get_extracted_links_page(pdf_hash: str):
  """
  Route to get page with extracted links from a PDF file.

  This function intercepts ``GET`` requests to ``/links/<pdf_hash>``.
  It looks for a PDF that matches the given hash.
  If found, it extracts links from that PDF and returns a ``200 OK`` response with them.
  If not, it returns a ``404 Not Found`` response.

  :param pdf_hash: MD5 hash of an uploaded PDF
  :return: An HTTP Response

  """

  # assert that PDF exists
  pdf_path = os.path.join(app.config['UPLOADS_FOLDER'], pdf_hash + ".pdf")
  if not os.path.exists(pdf_path):
    flask.abort(__make_error_response(404, ERR_MSG_PDF_NOT_FOUND))
  # extracts links from PDF
  urls = extractor.extract_all_urls(pdf_path)
  # send extracted links
  return flask.render_template("links.html", filename=pdf_hash, urls=urls)


@app.route("/mappings/<pdf_hash>", methods=['GET'])
def get_mappings(pdf_hash: str):
  """
  Route to get stored ``URI-R -> URI-M`` mappings from file.

  This function intercepts ``GET`` requests to ``/mappings/<pdf_hash>``.
  It looks for a PDF that matches the given hash.
  If found, it looks for stored ``URI-R -> URI-M`` mappings for that PDF, and returns a ``200 OK`` response with them.
  If either the PDF or the mappings are not found, it returns a ``404 Not Found`` response.

  :param pdf_hash: MD5 hash of an uploaded PDF to which the mappings correspond to
  :return: An HTTP Response

  """

  # assert that PDF exists
  pdf_path = os.path.join(app.config['UPLOADS_FOLDER'], pdf_hash + ".pdf")
  if not os.path.exists(pdf_path):
    flask.abort(__make_error_response(404, ERR_MSG_PDF_NOT_FOUND))
  # assert that mappings exist
  mapping_path = os.path.join(app.config['MAPPING_FOLDER'], pdf_hash + ".pdf.json")
  if not os.path.exists(mapping_path):
    flask.abort(__make_error_response(404, ERR_MSG_MAPPING_NOT_FOUND))
  # send mappings
  return flask.send_file(mapping_path)


@app.route("/robustify", methods=['POST'])
def robustify():
  """
  Route to robustify URIs in a PDF file.

  This function intercepts ``POST`` requests to ``/robustify``.
  It expects the request body to contain form data with two keys: ``filename`` and ``uris``.
  The ``filename`` is the MD5 hash of an uploaded PDF.
  The ``uris`` is a a subset of URIs from the PDF which should be robustified.

  For each URI, the function calls the Robust Links Service to create a ``URI-R -> URI-M`` mapping.
  The HTTP response `streams` each mapping as a JSON blob.
  The request completes when each URL is processed through the Robust Links Service.
  Upon completion, the generated ``URI-R -> URI-M`` mappings are stored in a file, which can be accessed via ``/mappings/<pdf_hash>``.
  Here, ``pdf_hash`` is the MD5 hash of the corresponding PDF.

  :return: An HTTP Response

  """

  req_json = flask.request.get_json()
  pdf_hash = req_json['filename']
  uris = req_json['uris']

  def generate():
    mappings = {}
    # robustify given uris
    for uri in uris:
      uri = uri.strip()
      res = requests.get(f"http://robustlinks.mementoweb.org/api/",
                         params={"url": uri},
                         headers={"Accept": "application/json"})
      try:
        # try converting response to JSON
        res_json: dict = res.json()
      except json.JSONDecodeError:
        # response is not JSON, handle accordingly
        payload = {
          "ok": False,
          "uri": uri,
          "error": f"Robust Links API returned a Non-JSON (HTTP {res.status_code}) for URI {uri}"
        }
      else:
        # response is JSON, handle accordingly
        if 'robust_links_html' in res_json:
          # handle responses with 'robust_links_html'
          payload = {
            "ok": res.ok,
            "uri": uri,
            "href_uri_r": res_json['robust_links_html']['original_url_as_href'].strip(),
            "href_uri_m": res_json['robust_links_html']['memento_url_as_href'].strip(),
          }
        elif 'friendly error' in res_json:
          # handle responses with 'friendly error'
          payload = {
            "ok": res.ok,
            "uri": uri,
            "error": f"{res_json['friendly error'].strip()} (HTTP {res.status_code})"
          }
        else:
          # response does not have expected fields
          payload = {
            "ok": False,
            "uri": uri,
            "error": f"Robust Links API returned an unknown JSON (HTTP {res.status_code}) for URI {uri}"
          }
      # append the payload into a dict, for saving later
      mappings[uri] = payload
      app.logger.info(payload)
      # stream progress for each uri
      yield json.dumps(payload) + "\n"
    # save mappings to file
    mapping_path = os.path.join(app.config['MAPPING_FOLDER'], pdf_hash + ".pdf.json")
    with open(mapping_path, "w") as f:
      json.dump(mappings, f)

  return app.response_class(generate(), content_type='application/octet-stream')


@app.route("/ldn/<pdf_hash>", methods=['GET'])
def get_ldn(pdf_hash: str, **ldn_args):
  """
  Route to generate an LDN payload which notifies the existence of ``URI-R -> URI-M`` mappings for a PDF.

  This function intercepts ``GET`` requests to ``/ldn/<pdf_hash>``.
  It looks for a PDF that matches the given hash.
  If found, it returns a ``200 OK`` response with the LDN payload.
  If not, it returns a ``404 Not Found`` response.

  :param pdf_hash: MD5 hash of an uploaded PDF to which the mappings correspond to
  :param ldn_args: optional args to use when generating the LDN payload
  :return: An HTTP Response

  """

  # assert that PDF exists
  pdf_path = os.path.join(app.config['UPLOADS_FOLDER'], pdf_hash + ".pdf")
  if not os.path.exists(pdf_path):
    flask.abort(__make_error_response(404, ERR_MSG_PDF_NOT_FOUND))
  # assert that PDF metadata exists
  pdf_meta_path = os.path.join(app.config['UPLOADS_FOLDER'], pdf_hash + ".pdf.txt")
  if not os.path.exists(pdf_meta_path):
    flask.abort(__make_error_response(404, ERR_MSG_PDF_META_NOT_FOUND))
  # get the original pdf name from metadata
  with open(pdf_meta_path) as f:
    pdf_name = f.readline()
  # get published time (if exists)
  mapping_path = os.path.join(app.config['MAPPING_FOLDER'], pdf_hash + ".pdf.json")
  if not os.path.exists(mapping_path):
    published_time = ""
  else:
    published_time = datetime.datetime.fromtimestamp(__file_creation_timestamp(mapping_path)).isoformat()
  # generate LDN payload
  ldn_args = {
    'hostname': flask.request.host_url.strip(' /'),
    'pdf_hash': pdf_hash,
    'pdf_name': pdf_name,
    'created_time': datetime.datetime.now().isoformat(),
    'published_time': published_time,
    **ldn_args
  }
  payload = flask.render_template("ldn.json", **ldn_args)
  # return LDN payload as JSON
  return flask.jsonify(flask.json.loads(payload))


@app.route("/ldn/<pdf_hash>", methods=['POST'])
def send_ldn(pdf_hash: str):
  """
  Route to send an LDN notifying the existence of ``URI-R -> URI-M`` mappings for a PDF, to an LDN server.

  This function intercepts ``POST`` requests to ``/ldn/<pdf_hash>``.
  It looks for a PDF that matches the given hash.
  If the PDF is found, it sends a LDN payload to the LDN server mentioned in the ``to`` field of the ``POST``.
  If the PDF is not found, it returns a ``404 Not Found`` response.
  Upon sending the LDN payload, it proxies back the response returned from the LDN inbox server.

  :param pdf_hash: MD5 hash of an uploaded PDF to which the mappings correspond to
  :return: An HTTP Response

  """

  # get JSON payload
  req_json = flask.request.get_json()
  to = req_json['to']
  # get LDN inbox URL
  res = requests.head(to)
  ldn_inbox_rel = "http://www.w3.org/ns/ldp#inbox"
  if ldn_inbox_rel not in res.links:
    return flask.jsonify({"ok": False, "error": f"The URL {to} does not reference an LDN Inbox"})
  # Get LDN inbox URL
  ldn_inbox_url = res.links[ldn_inbox_rel]['url']
  # Send LDN
  message = get_ldn(pdf_hash, **{'target_url': to, 'ldn_inbox_url': ldn_inbox_url}).get_json()
  res = requests.post(ldn_inbox_url, json=message, headers={'Content-Type': 'application/ld+json'})
  return flask.make_response(res.content, res.status_code)


@app.route("/preview/<pdf_hash>", methods=['GET'])
def ldn_preview(pdf_hash: str):
  """
  Route to preview the result from a LDN with ``URI-R -> URI-M`` mappings for a PDF.

  This function intercepts ``GET`` requests to ``/preview/<pdf_hash>``.
  It attempts to get the LDN payload matching the PDF hash.
  Upon found, it returns a ``200 OK`` HTTP response displaying the PDF and the robustified links.
  If not found, it returns a ``404 Not Found`` response.

  :param pdf_hash: MD5 hash of an uploaded PDF to which the mappings correspond to
  :return: An HTTP Response

  """
  # Get LDN
  ldn = get_ldn(pdf_hash, **{'target_url': "", 'ldn_inbox_url': ""}).get_json()
  return flask.render_template("preview.html", pdf_url=ldn['origin']['url'], mappings_url=ldn['object']['url'])


@app.route("/", methods=['GET'])
def get_upload_pdf_page():
  """
  Route to get page to upload a PDF file.

  This function intercepts ``GET`` requests to ``/``, and returns a page to select and upload a PDF file.
  Upon doing so, the page redirects to ``/links/<pdf_hash>``, where ``pdf_hash`` is the MD5 has of the uploaded PDF.

  :return: An HTTP Response

  """
  return flask.render_template("upload.html")


@app.route("/docs", methods=['GET'])
def redirect_docs_to_index():
  """
  Route to get documentation.

  This function intercepts ``GET`` requests to ``/docs``, and redirects them to ``'/docs/index.html``.

  :return: An HTTP 302 Redirect Response

  """
  return flask.redirect('/docs/index.html')


@app.route("/docs/<path:path>", methods=['GET'])
def get_docs_page(path: str):
  """
  Route to get documentation.

  This function intercepts ``GET`` requests to ``/docs/<page>``, and serves the documentation web page(s).

  :return: An HTTP Response

  """
  return flask.send_from_directory(app.config['DOCS_FOLDER'], path)


def __file_creation_timestamp(fp: str):
  """

  Try to get the date that a file was created, falling back to when it was
  last modified if that isn't possible.

  See http://stackoverflow.com/a/39501288/1709587 for explanation.

  """
  if platform.system() == 'Windows':
    return os.path.getctime(fp)
  else:
    stat = os.stat(fp)
    try:
      return stat.st_birthtime
    except AttributeError:
      # We're probably on Linux. No easy way to get creation dates here,
      # so we'll settle for when its content was last modified.
      return stat.st_mtime
