#!/usr/bin/python3

#  This file is part of Elixir, a source code cross-referencer.
#
#  Copyright (C) 2017  Mikaël Bouillot
#  <mikael.bouillot@bootlin.com>
#
#  Elixir is free software: you can redistribute it and/or modify
#  it under the terms of the GNU Affero General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  Elixir is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU Affero General Public License for more details.
#
#  You should have received a copy of the GNU Affero General Public License
#  along with Elixir.  If not, see <http://www.gnu.org/licenses/>.

from io import StringIO

realprint = print
outputBuffer = StringIO()

def print (arg, end='\n'):
    global outputBuffer
    outputBuffer.write (arg + end)

def log(desc, content, logfile='/tmp/webapplog.txt'):
    import logging
    logging.basicConfig(filename=logfile, level=logging.DEBUG)
    logging.debug(desc + ' ' + str(content))

# Enable CGI Trackback Manager for debugging (https://docs.python.org/fr/3/library/cgitb.html)
import cgitb
cgitb.enable()

import cgi
import os
from re import search, sub
from collections import OrderedDict

ident = ''
status = 200
# Split the URL into its components (project, version, cmd, arg)
m = search ('^/(.*)$', os.environ['SCRIPT_URL'])

log("Input ", os.environ['SCRIPT_URL'])
log("Input ", m.group(1))

if m:
    cmd = m.group (1)
    if cmd == 'grep':
        form = cgi.FieldStorage()
        word = form.getvalue ('i')
        log("Word ", word)
else:
    status = 404

if status == 404:
    realprint ('Status: 404 Not Found\n')
    exit()


basedir = os.environ['LXR_PROJ_DIR']
project = "linux"
os.environ['LXR_DATA_DIR'] = basedir + '/' + project + '/data';
os.environ['LXR_REPO_DIR'] = basedir + '/' + project + '/repo';

import sys
sys.path = [ sys.path[0] + '/..' ] + sys.path
import query

def do_query (*args):
    cwd = os.getcwd()
    os.chdir ('..')
    a = query.query (*args)
    os.chdir (cwd)

    # decode('ascii') fails on special chars
    # FIXME: major hack until we handle everything as bytestrings
    try:
        a = a.decode ('utf-8')
    except UnicodeDecodeError:
        a = a.decode ('iso-8859-1')
    a = a.split ('\n')
    del a[-1]
    return a

version = "latest"
if version == 'latest':
    tag = do_query ('latest')[0]
else:
    tag = version

url = "source"
projects = []
ident = ""

data = {
    'baseurl': '/' + project + '/',
    'tag': tag,
    'version': version,
    'url': url,
    'project': project,
    'projects': projects,
    'ident': ident,
    'breadcrumb': '<a class="project" href="'+version+'/source">/</a>',
}


lines = do_query ('versions')
va = OrderedDict()
for l in lines:
    m = search ('^([^ ]*) ([^ ]*) ([^ ]*)$', l)
    if not m:
        continue
    m1 = m.group(1)
    m2 = m.group(2)
    l = m.group(3)

    if m1 not in va:
        va[m1] = OrderedDict()
    if m2 not in va[m1]:
        va[m1][m2] = []
    va[m1][m2].append (l)

v = ''
b = 1
for v1k in va:
    v1v = va[v1k]
    v += '<li>\n'
    v += '\t<span>'+v1k+'</span>\n'
    v += '\t<ul>\n'
    b += 1
    for v2k in v1v:
        v2v = v1v[v2k]
        if v2k == v2v[0] and len(v2v) == 1:
            if v2k == tag: v += '\t\t<li class="li-link active"><a href="'+v2k+'/'+url+'">'+v2k+'</a></li>\n'
            else: v += '\t\t<li class="li-link"><a href="'+v2k+'/'+url+'">'+v2k+'</a></li>\n'
        else:
            v += '\t\t<li>\n'
            v += '\t\t\t<span>'+v2k+'</span>\n'
            v += '\t\t\t<ul>\n'
            for v3 in v2v:
                if v3 == tag: v += '\t\t\t\t<li class="li-link active"><a href="'+v3+'/'+url+'">'+v3+'</a></li>\n'
                else: v += '\t\t\t\t<li class="li-link"><a href="'+v3+'/'+url+'">'+v3+'</a></li>\n'
            v += '\t\t\t</ul></li>\n'
    v += '\t</ul></li>\n'

data['versions'] = v

log("Aloha", "Aloha")

if cmd == 'grep':
    data['title'] = project.capitalize ()+' source code: '+ident+' identifier ('+tag+') - Bootlin'

    lines = do_query ('grep', word)

    print ('<div class="lxrident">')
    
    num = int (len(lines))
    if num == 0:
        status = 404
    lines = iter (lines)

    print ('<h2>Referenced in '+str(num)+' files:</h2>')
    print ('<ul>')
    for i in range (0, num):
        l = next (lines)
        
        m = search ('^(.*?):(.*?):(.*)$', l)
        
        f  = m.group (1) # File path
        ln = m.group (2) # Line number
        lc = m.group (3) # Line content
        log("Path: ", f)
        log("LN: ", ln)
        log("Cont: ", lc)
        n = int(ln)
        print ('<li><a href="'+version+'/source/'+f+'#L'+str(n)+'"><strong>'+f+'</strong>, line: ' + str(n) +
                '</br> ' +
                '<p>' +
               str(lc) +
                '</p>' +
                '</a>')
    print ('</ul>')
    print ('</div>')

else:
    print ('Invalid request')

if status == 404:
    realprint ('Status: 404 Not Found')

import jinja2
loader = jinja2.FileSystemLoader (os.path.join (os.path.dirname (__file__), '../templates/'))
environment = jinja2.Environment (loader=loader)
template = environment.get_template ('layout_grep.html')

realprint ('Content-Type: text/html;charset=utf-8\n')
data['main'] = outputBuffer.getvalue()
realprint (template.render(data), end='')
