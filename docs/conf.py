import os
import sys
sys.path.insert(0, os.path.abspath('..'))

project = '{{LIBRARY_NAME}}'
copyright = '{{YEAR}}, {{AUTHOR_NAME}}'
author = '{{AUTHOR_NAME}}'
release = '{{VERSION}}'

extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.napoleon',
]

templates_path = ['_templates']
exclude_patterns = []

html_theme = 'sphinx_rtd_theme'