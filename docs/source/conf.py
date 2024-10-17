# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = 'wdm-simulator'
copyright = '2024, Sunjin Choi'
author = 'Sunjin Choi'

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    # 'extname',
    'sphinx.ext.todo',
    'sphinx.ext.autodoc',
    'sphinx.ext.graphviz',
    'sphinx.ext.autosectionlabel',
    'sphinxcontrib_hdl_diagrams',
]

templates_path = ['_templates']
exclude_patterns = []

todo_include_todos = True


# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

# html_theme = 'alabaster'
html_theme = 'sphinx_rtd_theme'
html_static_path = ['_static']
