#!/usr/bin/python

# l2py
# sync script for the RWTH L2P


#standard library imports
import re
import os
import os.path
import time
import datetime
import pprint
import _thread
import platform
import getpass
import argparse
import sys

#external libs
from bs4 import BeautifulSoup
import requests
from requests.auth import HTTPBasicAuth


baseurl = 'https://www2.elearning.rwth-aachen.de'
summary = '/foyer/summary/default.aspx'
course_summary = '/information/default.aspx'
course_materials = '/materials/default.aspx'

# parse arguments
parser = argparse.ArgumentParser(description="Sync L2P to a local directory")
parser.add_argument('-u', '--user', dest='user', help='specify username instead of asking interactively')
parser.add_argument('-p', '--password', dest='password', help='specify password instead of asking interactively')
parser.add_argument('-l', '--list-only', dest='listflag', action="store_true", help='only list files, do not download them')
parser.add_argument('-d', '--directory', dest='dir', default='L2P', help='specify directory to sync to (default: ./L2P)')
args = parser.parse_args()

basepath = os.path.join('.',args.dir)
if platform.system() == "Windows":
    basepath = os.path.abspath(basepath)
    basepath = '\\\\?\\'+basepath #the \\?\ prefix fixes path length cap on windows
if not os.path.exists(basepath):
    os.mkdir(basepath)

print("L2P sync script")
if not args.user:
    username = input("user: ")
else:
    username = args.user
if not args.password:
    password = getpass.getpass("password: ")
else:
    password = args.password
auth = (username,password)


#create a requests session
s = requests.session(auth=auth,timeout=10)

def downloadAll(dictionary, path, callback=None):
    """Walks a nested dictionary structure of of filenames and links and mirrors it
    to path. The optional callback is called after each individual file (e.g. for
    tracking progress)."""
    for name, value in dictionary.items():
        if type(value) == dict: # it is a folder
            newpath = os.path.join(path, escape(name))
            if os.path.exists(newpath):
                if not os.path.isdir(newpath):
                    print("%s already exists and is not a folder" % newpath, file=sys.stderr)
                    raise Error
            else:
                os.mkdir(newpath)
            downloadAll(value, newpath, callback=callback)
        else:
            if callback:
                callback(name)
            fpath = os.path.join(path,name)
            print("syncing %s" % name)
            r = s.get(value, prefetch=False)
            if os.path.exists(fpath):
                mtime = os.path.getmtime(fpath)
                then = time.mktime(time.strptime(r.headers['last-modified'],"%a, %d %b %Y %H:%M:%S GMT"))
                if then > mtime: #remote file is newer
                    with open(fpath, "wb") as f:
                        i = 0
                        for chunk in r.iter_content(chunk_size=1024):
                            f.write(chunk)
                else:
                    pass
            else:
                with open(fpath, "wb") as f:
                    i = 0
                    for chunk in r.iter_content(chunk_size=1024):
                        f.write(chunk)

def recCount(dictionary):
    """Recurses into a nested dictionary counting all non-dictionary items"""
    c = 0
    for k,v in dictionary.items():
        if type(v) == dict:
            c += recCount(v)
        else:
            c += 1
    return c

def scrapeFiles(url):
    """Parses file names and links from L2P pages, recursing into directories"""
    files = {}
    r = s.get(url)
    soup = BeautifulSoup(r.content)
    links = [i for i in soup.findAll('td', class_='ms-vb2') if i.find('a')]
    for i in links:
        name = i.a.get_text()
        url = i.a['href']
        if re.match( baseurl+"(\S+)"+"\?RootFolder=(\S+)", url): #it is a folder
            files[name] = scrapeFiles(url)
        else:
            files[name] = baseurl+url
    return files

def getCourses(summarypage):
    courses = {}
    soup = BeautifulSoup(summarypage)
    course_tags = [i for i in soup.findAll('td', class_='ms-vb2') if i.find('a') and not i.a.find('img')]
    for tag in course_tags:
        base = re.findall('(\S+)/information/default.aspx',tag.a['href'])
        title = tag.a.get_text()
        courses[title] = base[0]
    return courses

def printTree(dictionary, indentation):
    '''prettyprint a nested dictionary'''
    for k,v in dictionary.items():
        if type(v) == dict:
            print(indentation*'   '+k.upper()) # print directories in upper case
            printTree(v, indentation+1)
        else:
            print(indentation*'   '+k)

def escape(string):
    '''escapes characters in strings that are not allowed in
       Windows directory names.'''
    string = string.replace('.','')
    string = string.replace(':','')
    string = string.replace('/','')
    string = string.replace('\\','')
    string = string.replace('*','')
    string = string.replace('?','')
    string = string.replace('<','')
    string = string.replace('>','')
    string = string.replace('|','')
    string = string.replace('"','')
    return string

def buildDict(courses,callback=None):
    d = {}
    for k,v in courses.items():
        if callback:
            callback(k)
        d[k] = scrapeFiles(baseurl+v+course_materials)
    return d

class Progress():
    def __init__(self,total):
        self.total = total
        self.counter = 0

    def tick(self,name):
        self.counter += 1
        print("syncing %s. \t\t\t%d/%d (%d%%)" % (name, self.counter, self.total, self.counter/self.total * 100), end='\r')

class CourseProgress(Progress):
    def tick(self,name):
        self.counter += 1
        print("getting files for %s (course %d/%d)" % (name,self.counter,self.total))

if __name__ == "__main__":
    page = s.get(baseurl+summary).content
    courses = getCourses(page)
    p = CourseProgress(len(courses))
    print("Collecting Files")
    d = buildDict(courses,callback=p.tick)
    print("Found %d files in %d courses\n" % (recCount(d),len(courses)))
    if args.listflag: #pretty print all files
        printTree(d,0)
    else:
        total = recCount(d)
        p = Progress(total)
        print("Downloading Files")
        downloadAll(d,basepath,callback=p.tick)

