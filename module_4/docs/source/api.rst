API Reference
=============

Flask app and routes — ``app``
------------------------------

Routes registered by :func:`app.create_app`:

=========================  ======  ==========================================================
Route                      Method  Response
=========================  ======  ==========================================================
``/`` and ``/analysis``    GET     200 HTML Analysis page
``/pull-data``             POST    200 ``{"ok": true, "count": N}``; 409 ``{"busy": true}``; 500 on failure
``/update-analysis``       POST    200 ``{"ok": true}``; 409 ``{"busy": true}`` while a pull runs
=========================  ======  ==========================================================

Route handlers
~~~~~~~~~~~~~~

.. autofunction:: app.analysis

.. autofunction:: app.pull_data

.. autofunction:: app.update_analysis

App factory and helpers
~~~~~~~~~~~~~~~~~~~~~~~

.. automodule:: app
   :exclude-members: analysis, pull_data, update_analysis, app

Scraper — ``scrape``
--------------------

.. automodule:: scrape

Browser capture — ``auto_next_pages`` and ``capture_chrome_html``
-----------------------------------------------------------------

.. automodule:: auto_next_pages

.. automodule:: capture_chrome_html

Cleaning — ``clean``
--------------------

.. automodule:: clean

Loading — ``load_data``
-----------------------

.. automodule:: load_data

SQL queries — ``query_data``
----------------------------

.. automodule:: query_data

ORM model and queries — ``models`` and ``orm_queries``
------------------------------------------------------

.. automodule:: models
   :exclude-members: Base, metadata, registry

.. automodule:: orm_queries

Report generators
-----------------

.. automodule:: generate_query_results_pdf

.. automodule:: generate_limitations_pdf
