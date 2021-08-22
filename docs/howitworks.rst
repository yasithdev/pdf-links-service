How it Works
============

The PDF Links Service primarily uses the PyPDF2 package and the PDFIUM library (via the PyPDFIUM package) to extract URLs from PDF documents.
To obtain robust links for the extracted URLs, it uses the Robust Links API.

.. image:: /_static/functional-diagram.png
   :width: 600

Users of the PDF Links Service begin by uploading a PDF document.
This document is first processed using the PyPDF2 package to extract URLs from the PDF annotations (Step 1).
Following this, it is processed by the PDFIUM library to extract URLs from the PDF text (Step 2).
From the sets of URLs extracted from both methods, URLs extracted from the PDF annotations are given priority over URLs extracted from the PDF text.
We base this approach on our empirical finding that URLs extracted from Step 1 are less error-prone than URLs extracted from Step 2.

Next, the PDF Links Service allows users to robustify the extracted URLs.
Here, the user first selects all or some of the extracted URLs and robustifies them.
This robustification is done by calling the Robust Links API.
Upon robustifying each URL, the web interface displays the status of robustification, indicating whether or not it was successful.

Following this, the user can generate a Linked Data (LD) Notification to announce the availability of robustified URL mappings to a LD Server of choice.
Upon generating the LDN, the user can send it to that LD server.

Moreover, the user can preview the PDF and it robust links on a separate page.
This page uses the Robust Links CSS and JS to provide the option to either open the original resource, or an archived version of it (i.e., memento).

