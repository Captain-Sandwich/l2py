L2Py
====

Download Script for RWTH study material
---------------------------------------

author: Patrick Bethke 

language: Python (v3.2 compatible)

Explanation
-----------

l2py.py is a command-line utility that downloads study material from the RWTH Aachen's L2P platform.

The script mirrors all files to a local folder.

Installation
------------
L2Py has dependencies:
- [requests] [req]
- [BeautifulSoup] [bs]

Both are available on pip

    pip install BeautifulSoup requests

Usage
-----

    ./l2py.py

The script asks for your username and password and then starts to do its magic.

[bs]: http://www.crummy.com/software/BeautifulSoup/
[req]: http://docs.python-requests.org/en/latest/
