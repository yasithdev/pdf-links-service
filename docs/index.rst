PDF Links Service
=================

The `PDF Links Service </>`_ allows you to extract links from PDF documents, "robustify" them, and notify the
availability of robust links via Linked Data (LD) Notifications.

.. figure:: _static/overview.png
   :align: center
   :width: 600


Why "robustify" links?
---------------------------------------

Links to the web break all the time.
This behavior is observed in two forms:
1) Link Rot (where following the link yields a HTTP 404 error or equivalent) and
2) Content Drift (where the content following the link are changed over time, possibly to a point where it loses all
similarity with the originally linked content)

The fraction of articles containing references to web resources is growing steadily over time.
One of five Science, Technology, and Medicine (STM) articles suffer from reference rot, meaning it is impossible to revisit the web context that surrounds them some time after their publication `[source] <https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0115253>`_.


.. toctree::
   :maxdepth: 1

   usage
   howitworks
   setup
   api/index