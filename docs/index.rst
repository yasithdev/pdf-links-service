Robust PDFLinks
================

The `Robust PDFLinks </>`_ service allows you to extract links from PDF documents, "robustify" them, notify the
availability of robust links via Linked Data (LD) Notifications, and preview the PDF with its robust links.

.. figure:: _static/overview.png
   :align: center
   :width: 600


Why "Robustify" Links in PDFs?
---------------------------------------

Links to the web break all the time.
This behavior is observed in two forms:

1) **Link Rot** - Following the link yields a HTTP 404 error or equivalent
2) **Content Drift** - Content following the link are changed over time, possibly to a point where it loses all similarity with the originally linked content

The fraction of articles containing references to web resources (such as URLs) is growing steadily over time.
Here are some interesting facts from the world of Science, Technology, and Medicine.

1) *One* in *Five* scholarly articles with URLs suffer from reference rot,
   meaning it is impossible to revisit the web context that surrounds them some time after their publication.
   `[1] <https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0115253>`_
2) *Three* in *Four* scholarly articles with URLs suffer from content drift,
   meaning the content referenced by them have drifted away from what they were when originally referenced.
   `[2] <https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0167475>`_


.. toctree::
   :maxdepth: 1

   usage
   howitworks
   setup
   api/index