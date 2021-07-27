import ctypes
from typing import Set, List

import PyPDF2.pdf
import pypdfium
import logging

from errors import URLError
from util import Util


class Extractor:
  util = Util()

  def __extract_annot_urls(self, fp: str) -> Set[str]:
    """
    Extract Annotated URLs from PDF
    (Using PyPDF2)

    :param fp: Path to PDF
    :return: Set of Annotated URLs in PDF
    """
    urls = set()
    with open(fp, "rb") as file:
      pdf = PyPDF2.pdf.PdfFileReader(file)
      for page in pdf.pages:
        page: PyPDF2.pdf.PageObject = page.getObject()
        if "/Annots" in page:
          for annot in page["/Annots"]:
            annot = annot.getObject()
            if "/A" in annot:
              ann = annot["/A"].getObject()
            elif "/S" in annot:
              ann = annot["/S"].getObject()
            else:
              continue
            if "/URI" in ann:
              try:
                urls.add(self.util.canonicalize_url(ann["/URI"]))
              except URLError as e:
                logging.debug(e)
    return urls

  def __extract_text_urls(self, fp: str) -> Set[str]:
    """
    Extract Text URLs from PDF
    (Using PDFium)

    :param fp: Path to PDF
    :return: Set of Text URLs in PDF
    """
    urls = set()
    buf_len = 2048
    buffer = (ctypes.c_ushort * buf_len)()
    buffer_ = ctypes.cast(buffer, ctypes.POINTER(ctypes.c_ushort))
    # this line is very important, otherwise it would not work
    pypdfium.FPDF_InitLibraryWithConfig(pypdfium.FPDF_LIBRARY_CONFIG(2, None, None, 0))

    doc = pypdfium.FPDF_LoadDocument(fp, None)
    page_count = pypdfium.FPDF_GetPageCount(doc)
    for i in range(page_count):
      # load PDF page
      page = pypdfium.FPDF_LoadPage(doc, i)
      # load text in PDF page
      text = pypdfium.FPDFText_LoadPage(page)
      # Load links in PDF text
      links = pypdfium.FPDFLink_LoadWebLinks(text)
      link_count = pypdfium.FPDFLink_CountWebLinks(links)
      # get each URL
      for j in range(link_count):
        url_length = pypdfium.FPDFLink_GetURL(links, j, buffer_, buf_len)
        url_nums = buffer[:url_length - 1]
        url = "".join(map(chr, url_nums)).strip()
        try:
          urls.add(self.util.canonicalize_url(url))
        except URLError as e:
          logging.debug(e)
      pypdfium.FPDFLink_CloseWebLinks(links)
      pypdfium.FPDFText_ClosePage(text)
      pypdfium.FPDF_ClosePage(page)
    pypdfium.FPDF_CloseDocument(doc)
    return urls

  def extract_urls(self, fp: str) -> List[str]:
    """
    Extract All URLs from PDF
    (Using PyPDF2 and PDFium)

    :param fp: Path to PDF
    :return: Set of All URLs in PDF
    """
    # extract annotated URLs (baseline, always valid)
    annot_urls = set(self.__extract_annot_urls(fp))
    # extract full text URLs (error-prone)
    full_text_urls = set(self.__extract_text_urls(fp))
    # pick unique URLs from full_text_urls
    full_text_urls = self.util.pick_uniq_urls(full_text_urls)
    # pick URLs from full_text_urls do not match (exact/partial) any URL in annot_urls
    full_text_urls = self.util.pick_new_urls(full_text_urls, annot_urls)
    # concatenate, sort, and return
    return sorted(annot_urls.union(full_text_urls))
