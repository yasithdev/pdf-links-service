Link Extractor
==============

This module is responsible for extracting URI references from PDF documents.
It uses two libraries to perform this.

1. `PyPDF2 <https://pypi.org/project/PyPDF2/>`_ - A Pure-Python library built as a PDF toolkit.
2. `PyPDFIUM <https://pypi.org/project/pypdfium/>`_ - A Python wrapper for the `PDFIUM <https://github.com/chromium/pdfium/>`_ C/C++ library used by the Chromium project.

.. automodule:: pdflinks.extractor
.. autoclass:: pdflinks.extractor.Extractor
   :members:

