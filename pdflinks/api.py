import concurrent.futures
import datetime
import hashlib
import io
import json
import os

import flask
import requests

from .extractor import Extractor

app = flask.Flask(__name__)
app.config['UPLOADS_FOLDER'] = './pdfs'
app.config['MAPPING_FOLDER'] = './mappings'
app.config['DOCS_FOLDER'] = '../docs/_build/html'
extractor = Extractor()

ERR_TITLE = "Error!"
ERR_REQ_NOT_JSON = "Expected JSON payload"
ERR_PDF_NOT_FOUND = "The requested PDF file was not found"
ERR_PDF_META_NOT_FOUND = "The metadata for the requested PDF file was not found. Please try uploading the PDF again to generate metadata."
ERR_MAPPING_NOT_FOUND = "This PDF does not have any saved URI-R > URI-M mappings"
ERR_ONLY_PDF_ALLOWED = "You are only allowed to upload PDF files"
ERR_MALFORMED_LDN = "The LDN is malformed"
ERR_MISSING_PARAM_FILE = "Missing required parameter 'file'"
ERR_MISSING_PARAM_LD_SERVER_URL = "Missing required parameter 'ld_server_url'"
ERR_MISSING_PARAM_PDF_URL = "Missing required query parameter 'pdf_url'"
ERR_MISSING_PARAM_MAPPING_URL = "Missing required query parameter 'mapping_url'"


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
    return flask.abort(__make_error_response(400, ERR_MISSING_PARAM_FILE))
  # get file from the request
  file = flask.request.files['file']
  orig_filename = file.filename
  # ensure that the file is a pdf
  if file.mimetype != 'application/pdf':
    return flask.abort(__make_error_response(400, ERR_ONLY_PDF_ALLOWED))
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
    return flask.abort(__make_error_response(404, ERR_PDF_NOT_FOUND))
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
    return flask.abort(__make_error_response(404, ERR_PDF_NOT_FOUND))
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
    return flask.abort(__make_error_response(404, ERR_PDF_NOT_FOUND))
  # assert that mappings exist
  mapping_path = os.path.join(app.config['MAPPING_FOLDER'], pdf_hash + ".pdf.json")
  if not os.path.exists(mapping_path):
    return flask.abort(__make_error_response(404, ERR_MAPPING_NOT_FOUND))
  # send mappings
  return flask.send_file(mapping_path)


@app.route("/robustify", methods=['POST'])
def robustify():
  """
  Route to robustify URIs in a PDF file.

  This function intercepts ``POST`` requests to ``/robustify``.
  It expects the request body to contain form data with two keys: ``pdf_hash`` and ``uris``.
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
  pdf_hash = req_json['pdf_hash']
  uris = req_json['uris']

  def generate():
    # dict of generated mappings
    mappings = {}
    # robustify given uris (parallelism=5)
    with concurrent.futures.ThreadPoolExecutor(5) as executor:
      # list storing future results
      futures = []
      # run in parallel
      for uri in uris:
        futures.append(executor.submit(__call_robust_links_svc, uri.strip()))
      # process each future
      for future in concurrent.futures.as_completed(futures):
        payload = future.result()
        # append the payload into a dict, for saving later
        mappings[uri] = payload
        # stream a JSON response
        yield json.dumps(payload) + "\n"
    # write generated mappings to file
    mapping_path = os.path.join(app.config['MAPPING_FOLDER'], pdf_hash + ".pdf.json")
    with open(mapping_path, "w") as f:
      json.dump(mappings, f)

  return app.response_class(generate(), content_type='application/octet-stream')


@app.route("/ldn/<pdf_hash>", methods=['GET'])
def get_ldn_json(pdf_hash: str):
  """
  Route to get an LDN payload which notifies the existence of ``URI-R -> URI-M`` mappings for a PDF.

  This function intercepts ``GET`` requests to ``/ldn/<pdf_hash>``.
  It looks for a PDF that matches the given hash.
  If found, it returns a ``200 OK`` response with the LDN payload.
  If not, it returns a ``404 Not Found`` response.

  :param pdf_hash: MD5 hash of an uploaded PDF to which the mappings correspond to
  :return: An HTTP Response

  """

  # get LD server URL from query params
  ld_server_url = __get_ld_server_url_from_query_params()
  # resolve LDP inbox URL from LD server
  ldp_inbox_url = __resolve_ldp_inbox_url(ld_server_url)
  # generate LDN payload
  return __generate_ldn_payload(pdf_hash, ld_server_url, ldp_inbox_url)


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

  # get LD server URL from request body
  ld_server_url = __get_ld_server_url_from_request_body()
  # resolve LDP inbox URL from LD server
  ldp_inbox_url = __resolve_ldp_inbox_url(ld_server_url)
  # generate LDN payload
  ldn_payload = __generate_ldn_payload(pdf_hash, ld_server_url, ldp_inbox_url).get_json()
  # send LDN payload to LDP inbox of LD server
  res = requests.post(ldp_inbox_url, json=ldn_payload, headers={'Content-Type': 'application/ld+json'})
  # proxy response from LD server
  return flask.make_response(res.content, res.status_code)


@app.route("/preview", methods=['POST'])
def request_ldn_preview():
  """
  Route to request a preview for a LDN which offers ``URI-R -> URI-M`` mappings of a PDF.

  This function intercepts ``POST`` requests to ``/preview``.
  It expects a LDN payload in the request body, and extracts from it the URLs of the PDF and its mappings.
  If the payload is not a LDN or is malformed, it returns a ``400 Bad Request`` response.
  Next, it returns a ``302`` HTTP redirect to a preview page for that LDN.

  :return: An HTTP Response

  """
  # get request body as JSON
  ldn_payload = __get_request_body_as_json()
  # get PDF url and mapping URL from LDN payload
  try:
    pdf_url = ldn_payload['origin']['url']
    mapping_url = ldn_payload['object']['url']
  except KeyError:
    return flask.abort(__make_error_response(400, ERR_MALFORMED_LDN))
  return flask.redirect(f"/preview?pdf_url={pdf_url}&mapping_url={mapping_url}")


@app.route("/preview", methods=['GET'])
def get_ldn_preview():
  """
  Route to get a preview of a PDF and its ``URI-R -> URI-M`` mappings.

  This function intercepts ``GET`` requests to ``/preview``.
  It expects two query parameters, namely, ``pdf_url`` (i.e., the URL of a PDF) and ``mapping_url`` (i.e., the URI-R -> URI-M mappings for URIs in that PDF).
  If any of these parameters are not found, it will return a ``400 Bad Request`` HTTP response.
  If both parameters exist, it will return a ``200 OK`` HTTP response with the preview page HTML.

  :return: An HTTP Response

  """
  # get query params
  params = flask.request.args
  if 'pdf_url' not in params:
    return flask.abort(__make_error_response(400, ERR_MISSING_PARAM_PDF_URL))
  if 'mapping_url' not in params:
    return flask.abort(__make_error_response(400, ERR_MISSING_PARAM_MAPPING_URL))
  pdf_url = params.get('pdf_url')
  mapping_url = params.get('mapping_url')
  return flask.render_template("preview.html", pdf_url=pdf_url, mappings_url=mapping_url)


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
    body = flask.render_template('error.html', title=ERR_TITLE, message=message)
  elif mimes.accept_json:
    body = {"ok": False, "timestamp": datetime.datetime.utcnow().isoformat(), "error": message}
  else:
    body = message
  return flask.make_response(body, status)


def __call_robust_links_svc(uri: str):
  """
  Call the Robust Links Service on a URI, and return the status of its robustification.

  A success response has the following fields.

  * ``ok``: always True
  * ``uri``: The URL which was sent to the Robust Links API
  * ``href_uri_r``: Robust Link pointing to the original resource
  * ``href_uri_m``: Robust Link pointing to an archived copy of the original resource (i.e., memento)

  An error response has the following fields.

  * ``ok``: always False
  * ``uri``: The URL which was sent to the Robust Links API
  * ``error``: A friendly description of the error

  :param uri: the URL to robustify
  :return: the status of robustification

  """

  # log the function call
  app.logger.info(f"Submitted request to RL Service for URL: {uri}")

  # send the request
  params = {"url": uri, "anchor_text": uri}
  headers = {"Accept": "application/json"}
  res = requests.get(f"http://robustlinks.mementoweb.org/api/", params=params, headers=headers)

  def error_response(__errmsg: str):
    app.logger.warn(__errmsg)
    return {"ok": False, "uri": uri, "error": __errmsg}

  def success_response(__rl: any, __uri_r_key='original_url_as_href', __uri_m_key='memento_url_as_href'):
    app.logger.info(f"RL Service robustified URL: {uri}")
    return {"ok": True, "uri": uri, "href_uri_r": minify(__rl[__uri_r_key]), "href_uri_m": minify(__rl[__uri_m_key])}

  def minify(html: str):
    return html.replace('\n', '').strip()

  try:
    # try converting response to JSON
    res_json: dict = res.json()
  except json.JSONDecodeError:
    # if the response is not JSON
    return error_response(f"Robust Links API returned a Non-JSON (HTTP {res.status_code}) for URI {uri}")
  else:
    # if the response is JSON
    if 'robust_links_html' in res_json:
      # handle responses with 'robust_links_html'
      return success_response(res_json['robust_links_html'])
    elif 'friendly error' in res_json:
      # handle responses with 'friendly error'
      return error_response(f"{res_json['friendly error'].strip()} (HTTP {res.status_code})")
    else:
      # handle responses that do not have the expected fields
      return error_response(f"Robust Links API returned an unknown JSON (HTTP {res.status_code}) for URI {uri}")


def __generate_ldn_payload(pdf_hash: str, ld_server_url: str, ldp_inbox_url: str):
  """
  Generate an LDN payload for a PDF, given the ``pdf_hash``, ``ld_server_url``, and ``ldp_inbox_url``.

  This function checks if the PDF exists and if not, returns a ``400 Bad Request`` HTTP response.
  Next, it checks if the PDF metadata exists and if not, returns a ``400 Bad Request`` HTTP response.
  Upon doing so, it gets the original PDF name from the metadata.

  Next, it checks if URI-R -> URI-M mappings exists for the PDF and if not, returns a ``400 Bad Request`` HTTP response.
  Upon doing so, it gets the last modified time of the URI-R -> URI-M mappings.
  Using this information, it generates the LDN payload and returns it with a ``200 OK`` HTTP response.

  :param pdf_hash: MD5 hash of an uploaded PDF
  :param ld_server_url: URL of the Linked Data (LD) Server
  :param ldp_inbox_url: URL of the LDP inbox of the given LD Server
  :return: An LDN as a JSON response

  """
  # assert that PDF exists
  pdf_path = os.path.join(app.config['UPLOADS_FOLDER'], pdf_hash + ".pdf")
  if not os.path.exists(pdf_path):
    return flask.abort(__make_error_response(404, ERR_PDF_NOT_FOUND))
  # assert that PDF metadata exists
  pdf_meta_path = os.path.join(app.config['UPLOADS_FOLDER'], pdf_hash + ".pdf.txt")
  if not os.path.exists(pdf_meta_path):
    return flask.abort(__make_error_response(404, ERR_PDF_META_NOT_FOUND))
  # get the original pdf name from metadata
  with open(pdf_meta_path) as f:
    pdf_name = f.readline()
  # assert that the URI-R -> URI-M mappings exist for the PDF
  mapping_path = os.path.join(app.config['MAPPING_FOLDER'], pdf_hash + ".pdf.json")
  if not os.path.exists(mapping_path):
    return flask.abort(__make_error_response(404, ERR_MAPPING_NOT_FOUND))
  # last modified time of the URI-R -> URI-M mappings
  mapping_mtime = datetime.datetime.fromtimestamp(os.path.getmtime(mapping_path)).isoformat()
  # generate LDN payload
  ldn_args = {
    'hostname': flask.request.host_url.strip(' /'),
    'pdf_hash': pdf_hash,
    'pdf_name': pdf_name,
    'created_time': datetime.datetime.now().isoformat(),
    'published_time': mapping_mtime,
    'ld_server_url': ld_server_url,
    'ldp_inbox_url': ldp_inbox_url
  }
  payload = flask.render_template("ldn.json", **ldn_args)
  # return LDN payload as JSON
  return flask.jsonify(flask.json.loads(payload))


def __get_request_body_as_json():
  """
  Parse the request body as JSON, and return the parsed object.

  If the body cannot be parsed as JSON, it returns a ``400 Bad Request`` HTTP response.

  :return: Parsed Request body as an object

  """
  try:
    # try generating JSON from request body
    return flask.request.get_json()
  except json.JSONDecodeError:
    # if body is not JSON, abort request
    return flask.abort(__make_error_response(400, ERR_REQ_NOT_JSON))


def __get_ld_server_url_from_request_body(key='ld_server_url'):
  """
  Parse the request body as JSON, and return the LD server URL given in it.

  If the body cannot be parsed as JSON, or if ``key`` does not exist, it returns a ``400 Bad Request`` HTTP response.

  :param key: Key to extract from request body (default='ld_server_url`)
  :return: The LD Server URL given in the request body

  """
  # get request body as JSON
  req_json = __get_request_body_as_json()
  # assert that LD server URL exists in request body
  if key not in req_json:
    return flask.abort(__make_error_response(400, ERR_MISSING_PARAM_LD_SERVER_URL))
  return req_json[key]


def __get_ld_server_url_from_query_params(key='ld_server_url'):
  """
  Parse the request query params and return the LD server URL given in it.

  If ``key`` does not exist in the request query params, it returns a ``400 Bad Request`` HTTP response.

  :param key: Key to extract from request query params (default='ld_server_url`)
  :return: The LD Server URL given in the request query params

  """
  # assert that LD server URL exists in request query params
  if key not in flask.request.args:
    return flask.abort(__make_error_response(400, ERR_MISSING_PARAM_LD_SERVER_URL))
  # return LD server URL from request query params
  return flask.request.args.get(key)


def __resolve_ldp_inbox_url(ld_server_url: str):
  """
  Return the URL of the LDP inbox of the Linked Data (LD) service found at the ``ld_server_url``.

  This function performs a HEAD request to the ``ld_server_url``, and parses the link headers of the response.
  If a LDP inbox URL is found in the link header, it returns it.
  If not found, it returns a ``400 Bad Request`` HTTP response.

  :param ld_server_url: URL of the Linked Data (LD) server
  :return: The URL of the LDP inbox of the LD server

  """
  # Send HTTP HEAD request to LD Server URL
  res = requests.head(ld_server_url)
  # Get LDP Inbox URL from Link Header
  ldn_inbox_rel = "http://www.w3.org/ns/ldp#inbox"
  if ldn_inbox_rel not in res.links:
    return flask.abort(__make_error_response(400, f"The URL {ld_server_url} is not an LD Server"))
  return res.links[ldn_inbox_rel]['url']
