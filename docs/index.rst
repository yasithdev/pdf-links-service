===============
Robust PDFLinks
===============


Introduction
============

The `Robust PDFLinks </>`_ service allows you to extract links from PDF documents, "robustify" them, notify the
availability of robust links via Linked Data (LD) Notifications, and preview the PDF with its robust links.

.. figure:: _static/overview.png
   :align: center
   :width: 600


Why "Robustify" Links in PDFs?
------------------------------

Links to the web can break over time, in two forms:

1. **Link Rot** - Over time, the referenced web content had gone missing (i.e., it returns a HTTP 404 or equivalent)
2. **Content Drift** - Over time, the referenced web content had changed, possibly to a point where it's entirely different from the original.

The fraction of scholarly articles that reference web resources (via URLs) is growing steadily over time.
Here are some interesting facts about scholarly articles in the areas of Science, Technology, and Medicine.

1. *One in five* scholarly articles suffer from *reference rot* `[1] <https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0115253>`_
2. *Three in four* scholarly articles suffer from *content drift* `[2] <https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0167475>`_

This implies that for a majority of scholarly articles, the referenced web content could become inaccessible over time,
and their content could drift away from the original, both of which are detrimental to the scholarly world and beyond.

**We developed the *Robust PDFLinks* service to proactively combat this problem.
Through this, one could discover URLs in a PDF document, and preserve a copy of their content in Web Archives before
they are gone forever.**


Basics
======

.. toctree::

   basics/works
   basics/usage
   basics/setup

Code Manual
===========

.. toctree::
   :maxdepth: 1

   code/index
