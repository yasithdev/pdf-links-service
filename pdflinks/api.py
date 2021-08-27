import concurrent.futures
import hashlib
import io
import json
import os

import flask
import requests

from .extractor import Extractor
from .util import APIUtil

app = flask.Flask(__name__)
app.config['UPLOADS_FOLDER'] = './pdfs'
app.config['MAPPING_FOLDER'] = './mappings'
app.config['DOCS_FOLDER'] = '../docs/_build/html'
extractor = Extractor()
util = APIUtil(app)
executor = concurrent.futures.ThreadPoolExecutor(5)


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
    return flask.abort(util.make_error_res(400, util.ERR_MISSING_PARAM_FILE))
  # get file from the request
  file = flask.request.files['file']
  orig_filename = file.filename
  # ensure that the file is a pdf
  if file.mimetype != 'application/pdf':
    return flask.abort(util.make_error_res(400, util.ERR_ONLY_PDF_ALLOWED))
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
    return flask.abort(util.make_error_res(404, util.ERR_PDF_NOT_FOUND))
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
    return flask.abort(util.make_error_res(404, util.ERR_PDF_NOT_FOUND))
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
    return flask.abort(util.make_error_res(404, util.ERR_PDF_NOT_FOUND))
  # assert that mappings exist
  mapping_path = os.path.join(app.config['MAPPING_FOLDER'], pdf_hash + ".pdf.json")
  if not os.path.exists(mapping_path):
    return flask.abort(util.make_error_res(404, util.ERR_MAPPING_NOT_FOUND))
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

  For each URI, the function calls the Robust PDFLinks service to create a ``URI-R -> URI-M`` mapping.
  The HTTP response `streams` each mapping as a JSON blob.
  The request completes when each URL is processed through the Robust PDFLinks service.
  Upon completion, the generated ``URI-R -> URI-M`` mappings are stored in a file, which can be accessed via ``/mappings/<pdf_hash>``.
  Here, ``pdf_hash`` is the MD5 hash of the corresponding PDF.

  :return: An HTTP Response

  """

  req_json = flask.request.get_json()
  pdf_hash = req_json['pdf_hash']
  uris = req_json['uris']

  def run():
    # dict of generated mappings
    mappings = {}
    # local list storing future results
    futures = []
    try:
      # submit robustification requests
      for uri in uris:
        futures.append(executor.submit(util.call_robust_links_svc, uri.strip()))
      # process each future as completed
      for future in concurrent.futures.as_completed(futures):
        payload = future.result()
        uri = payload["uri"]
        # append the payload into a dict, for saving later
        mappings[uri] = payload
        # yield a JSON response
        yield json.dumps(payload) + "\n"
    except GeneratorExit:
      app.logger.info(f"client {flask.request.host_url} disconnected, cleaning up resources.")
      for future in futures:
        future.cancel()
    finally:
      app.logger.info("writing generated mappings to file.")
      # write generated mappings to file
      mapping_path = os.path.join(app.config['MAPPING_FOLDER'], pdf_hash + ".pdf.json")
      with open(mapping_path, "w") as f:
        json.dump(mappings, f)

  return app.response_class(run(), content_type='application/octet-stream')


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
  ld_server_url = util.get_ld_server_url_from_query_params()
  # resolve LDP inbox URL from LD server
  ldp_inbox_url = util.resolve_ldp_inbox_url(ld_server_url)
  # generate LDN payload
  return util.generate_ldn_payload(pdf_hash, ld_server_url, ldp_inbox_url)


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
  ld_server_url = util.get_ld_server_url_from_req_payload()
  # resolve LDP inbox URL from LD server
  ldp_inbox_url = util.resolve_ldp_inbox_url(ld_server_url)
  # generate LDN payload
  ldn_payload = util.generate_ldn_payload(pdf_hash, ld_server_url, ldp_inbox_url).get_json()
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
  ldn_payload = util.get_req_payload_as_json()
  # get PDF url and mapping URL from LDN payload
  try:
    pdf_url = ldn_payload['origin']['url']
    mapping_url = ldn_payload['object']['url']
  except KeyError:
    return flask.abort(util.make_error_res(400, util.ERR_MALFORMED_LDN))
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
    return flask.abort(util.make_error_res(400, util.ERR_MISSING_PARAM_PDF_URL))
  if 'mapping_url' not in params:
    return flask.abort(util.make_error_res(400, util.ERR_MISSING_PARAM_MAPPING_URL))
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
