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

#external libs
from bs4 import BeautifulSoup
import requests
from requests.auth import HTTPBasicAuth


baseurl = 'https://www2.elearning.rwth-aachen.de'
summary = '/foyer/summary/default.aspx'
course_summary = '/information/default.aspx'
course_materials = '/materials/default.aspx'

basepath = os.path.join('.','L2P')
if platform.system() == "Windows":
    basepath = os.path.abspath(basepath)
    basepath = '\\\\?\\'+basepath #the \\?\ prefix fixes path length cap on windows

# parse arguments
parser = argparse.ArgumentParser(description="Sync L2P to a local directory")
parser.add_argument('-u', '--user', dest='user', help='specify username instead of asking interactively')
parser.add_argument('-p', '--password', dest='password', help='specify password instead of asking interactively')
parser.add_argument('-l', '--list-only', dest='listflag', action="store_true", help='only list files, do not download them')
args = parser.parse_args()

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

class Course:
    def __init__(self,name='', link='', files={}):
        self.name = name
        self.link = link
        self.files = files
        self.total = 0 #total number of files

    def __repr__(self):
        return self.name

    def __str__(self):
        return self.name

    def items(self):
        return self.files.items()

    def scrapeFiles(self,url):
        files = {}
        r = s.get(url)
        soup = BeautifulSoup(r.content)
        links = [i for i in soup.findAll('td', class_='ms-vb2') if i.find('a')]
        for i in links:
            name = i.a.get_text()
            path = i.a['href']
            if re.match( baseurl+self.link+course_materials+"\?RootFolder=(\S+)", path): #it is a folder
                files[name] = self.scrapeFiles(path)
            else:
                files[name] = path
        return files

    def downloadAll(self, dictionary, path):
        for name, value in dictionary.items():
            if type(value) == dict: # it is a folder
                newpath = os.path.join(path, escape(name))
                if os.path.exists(newpath):
                    if not os.path.isdir(newpath):
                        print("%s already exists and is not a folder" % newpath)
                        raise Error
                else:
                    os.mkdir(newpath)
                self.downloadAll( value, newpath )
            else:
                url = baseurl + value
                fpath = os.path.join(path,name)
                print("syncing %s" % name)
                r = s.get(url, prefetch=False)
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
    
    def walk(self):
        url = baseurl + self.link
        url = url + course_materials
        self.files = self.scrapeFiles(url)
        self.total = recCount(self.files)
    
    def sync(self):
        base = os.path.join(basepath, escape(self.name))
        if not os.path.exists(base):
            os.makedirs(base)
        self.downloadAll(self.files, base)

def recCount(dictionary):
    c = 0
    for k,v in dictionary.items():
        if type(v) == dict:
            c += recCount(v)
        else:
            c += 1
    return c

def getCourses(summarypage):
    courses = []
    soup = BeautifulSoup(summarypage)
    course_tags = [i for i in soup.findAll('td', class_='ms-vb2') if i.find('a') and not i.a.find('img')]
    for tag in course_tags:
        base = re.findall('(\S+)/information/default.aspx',tag.a['href'])
        title = tag.a.get_text()
        courses.append(Course(name=title, link=base[0]))
    return courses

def printTree(dictionary, indentation):
    '''prettyprint a directory listing'''
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

if __name__ == "__main__":
    page = s.get(baseurl+summary).content
    courses = getCourses(page)
    print("Collecting Files")
    for c in courses:
        c.walk()
    print("Found %d files in %d courses\n" % (sum(map(recCount,courses)),len(courses)))
    if args.listflag: #pretty print all files
        for c in courses:
            printTree({c.name: c.files}, 0)
    else:
        print("Downloading Files")
        for c in courses:
            c.sync()

