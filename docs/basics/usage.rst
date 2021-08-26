Using the Web Interface
=======================

The Robust PDFLinks service provides a web interface to experiment with the process of robustifying URLs in PDF
documents and notifying Linked Data (LD) servers of the creation of Robust Links.

The diagram below summarizes the interaction of a user with the Robust PDFLinks service.

.. image:: /_static/interaction-diagram.png
   :width: 600


The interaction begins with users uploading a PDF document to the Robust PDFLinks service.
The page for uploading a PDF is illustrated below.

.. image:: /_static/1-upload-pdf.png
   :width: 600

Here, users first select a PDF document by clicking on the "Browse" button (1).
Upon doing so, the name of the selected PDF document is displayed (2).
Next, they can upload the PDF document by clicking on the "Upload" button (3).
Once they click on the "Upload" button (4), the selected PDF begins to upload.
They can also open the Robust PDFLinks Documentation by clicking on the "Docs" button (4) on the navigation bar.

Upon completion of the upload, the browser redirects the users to the next page, which is illustrated below.

.. image:: /_static/2-process-links.png
   :width: 600

Here, the users can open the uploaded PDF by clicking on the link shown by (5).
The URLs extracted from the PDF are displayed on the "Extracted Links" section.
Here, the users can either select/deselect all URLs (6) or pick some URLs (7) to robustify.
Next, they can click on the "Robustify" button (8) to begin the robustification process.

Note that this process takes a while to execute.
To make it easier to track the progress, the page displays a spinner (9) indicating that URLs are being robustified,
and also the progress of robustification (10).
As each URL is robustified, the robustification result is logged below the progress indicators.
Successful robustifications are denoted in *green*, whereas failed robustifications are denoted in *yellow*.
For each successful robustification, two links are displayed:
1) the link to the original resource (i.e, URI-R) and
2) the link to the archived resource (i.e., URI-M) (11).
Each link is accompanied by a "Copy" button (12) which lets users copy the HTML of that link.
Upon the completion of robustification, the generated robust links are written into a file on the server.

.. image:: /_static/3-send-ldn.png
   :width: 600

Next, the users can notify a Linked Data (LD) server of the existence of robust links for the PDF.
They first enter a URL of the LD server that they wish to notify (13), and click on the "Preview LDN" button (14)
to preview the LDN payload on the "LDN Preview" section underneath.
Upon doing this, they can click on the "Send LDN" button (15) to send the LDN to the specified LD Server.
They can also preview the PDF and its robust links on a separate page by clicking the "Preview Result" button (16).

.. image:: /_static/4-preview.png
   :width: 600

In the preview page, the PDF document is displayed in the left, and the Robust Links are displayed on the right.
This page uses the Robust Links CSS/JS to function.
The "Robust Links" section on the right, displays the Robust Links of the PDF document.
The original resource pointed by the URL can be opened by either clicking on the respective URL (17).
In addition, the dropdown expander (18) can be clicked on to reveal the robust links menu (19).
In this menu, users are able to navigate to either the original resource or an archived copy of that resource.
