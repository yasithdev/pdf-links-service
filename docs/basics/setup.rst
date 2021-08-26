Running the Service Locally
===========================

.. code-block:: bash

   # clone the repo from github (assuming 'git' is installed)
   git clone git@github.com:yasithmilinda/pdf-links-service.git

   # navigate to the cloned repo
   cd pdf-links-service/

   # (recommended, but optional) create and activate a virtual python environment
   python3 -m venv <name_of_virtual_env>
   source <name_of_virtual_env>/bin/activate

   # install dependencies for the robust pdflinks service
   pip install -r pdflinks/requirements.txt

   # (optional) install dependencies for the robust pdflinks docs
   pip install -r docs/requirements.txt

   # (optional) create docs (HTML)
   make html

   # (optional) create docs (PDF)
   make latexpdf

   # start the service
   make