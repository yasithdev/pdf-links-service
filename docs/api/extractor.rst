Link Extractor
==============

This module is responsible for extracting URI references from PDF documents.
It uses two libraries to achieve this,

* `PyPDF2 <https://pypi.org/project/PyPDF2/>`_
   A Pure-Python library built as a PDF toolkit.
   We use PyPDF2 to extract annotated URI references from PDF documents.

* `PyPDFIUM <https://pypi.org/project/pypdfium/>`_
   A simply python wrapper for `PDFIUM <https://github.com/chromium/pdfium/>`_.
   We use PDFIUM to extract URI references from the PDF text.

.. automodule:: pdflinks.extractor
.. autoclass:: pdflinks.extractor.Extractor
   :members:

