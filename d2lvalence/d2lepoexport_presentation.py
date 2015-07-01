"""
Provides functions for processing ePortfolio presentation objects
into downloadable HTML files.
"""
from bs4 import BeautifulSoup

import eportfolio

import urllib.request
import urllib.parse
import os
import sys
import datetime
import tempfile


###############
# Foundations #
###############

DOMAIN = "https://uwosh-beta.courses.wisconsin.edu"
"""
For use in getting files from links in the first page of the presentation.
Will need to be customized to your domain.
"""

"""
The fileDict is a foundational tool for collecting information on files and
objects that need to be downloaded into the presentation files. Its structure
if given here for clarity.
fileDict = {
            'pageUrls': [DOMAIN + <epObject.ViewLink attribute>],
            'pageFileNames': [<webpage file name>],
            'pageIds': [<epObject.ObjectId attribute>],
            'fileUrls': [DOMAIN + <address of embedded eportfolio artifact>],
            'fileIds': [<epObject.ObjectId attribute>],
            'fileNames': [<epFileArtifact.fileName attribute>],
            'cssUrls': [<web addresses of css files>],
            'cssFileNames':[<names of css files>],
            'imgUrls': [<web addresses of d2l's presentation images>],
            'imgFileNames': [<names of formatting image files>]
           }
"""


def make_file_dict():
    """
    For collecting links to enable the efficient download of files used by the
    presentation.
    """
    fileDict = {'pageUrls': [],
                'pageFileNames': [],
                'pageIds': [],
                'fileUrls': [],
                'fileIds': [],
                'fileNames': [],
                'cssUrls': [],
                'cssFileNames': [],
                'imgUrls': [],
                'imgFileNames': []}
    return fileDict


def make_soup(url):
    """
    Makes a BeautifulSoup object from a url.
    
    Parameters:
        url: string url for webpage to parse
    """
    htmlFile = urllib.request.urlopen(url).read()
    soup = BeautifulSoup(htmlFile)
    return soup


##########################
# Functions to get files #
##########################


def get_pages(epObject, fileDict):
    """
    Populates the 'pages' list in the fileDict with a dictionary containing
     static addresses, file names, and unique object IDs for pages in a
     presentation. Returns populated fileDict.

    Parameters:
        epObject: an ePortfolio presentation object from
         d2lepoexport.get_ep_object_properties or
         d2lepoexport.get_ep_presentation.
    """
    homePage = DOMAIN + epObject.ViewLink
    soup = make_soup(homePage)
    fileDict['pageUrls'].append(homePage)
    fileDict['pageFileNames'].append('index.html')
    fileDict['pageIds'].append(str(epObject.ObjectId))
    for a in soup.find_all('a', {'href': 'javascript://'}):
        if a['onclick'].find('GotoPage') > 0:
            pageId = get_page_id(str(a['onclick']), str(epObject.ObjectId))
            if pageId not in fileDict['pageIds']:
                address = homePage + "&pageId={0}".format(pageId)
                fileName = a.string.replace(' ', '').lower() + ".html"
                fileDict['pageUrls'].append(address)
                fileDict['pageFileNames'].append(fileName)
                fileDict['pageIds'].append(pageId)
    return fileDict


def get_page_id(onclick, objectId):
    """
    """
    beginIndex = onclick.find(objectId) + len(objectId) + 1
    pageId = onclick[beginIndex:]
    endIndex = 0
    nextCharacter = pageId[endIndex]
    while nextCharacter.isdigit():
        endIndex += 1
        nextCharacter = pageId[endIndex]
    pageId = pageId[:endIndex]
    return pageId

def get_epo_id(href):
    """
    Returns unique identifier for an ePortfolio element in a presentation.

    Parameters:
        href: web address from <a> tag attribute 'href' as a string
        objectId: unique identifier for ePortfolio presentation as a string
    """
    beginIndex = href.find("contextId=") + len("contextId=")
    epoId = href[beginIndex:]
    endIndex = 0
    nextCharacter = epoId[endIndex]
    while nextCharacter.isdigit():
        endIndex += 1
        nextCharacter = epoId[endIndex]
    epoId = epoId[:endIndex]
    return epoId


def get_embedded_object(soup, fileDict, uc):
    """
    Returns fileDict updated with ePortfolio object IDs of objects embedded in
     the presentation. fileDict['files'] list will be populated with objects
     linked within a single presentation page.

    Parameters:
        soup: a BeautifulSoup object created from a presentation page
        fileDict: dict of all files linked to in a presentation
    """
    for a in soup.find_all('a'):
        href = str(a['href'])
        if href.find('d2lfile') > 0:
            epoId = get_epo_id(href)
            if epoId not in fileDict['fileIds']:
                fileDict['fileIds'].append(epoId)
                fileDict['fileUrls'].append(DOMAIN + href)
                fileName = d2lepoexport.get_ep_object_properties(uc, epoId).\
                    FileName.strip()
                fileDict['fileNames'].append(fileName)
    return fileDict


def get_css(soup, fileDict):
    """
    Returns fileDict updated with addresses of CSS files linked to in a single
     presentation page. fileDict['css'] list will be populated with any CSS
     links found.

    Parameters:
        soup: a BeautifulSoup object created from a presentation page
        fileDict: dict of all files linked to in a presentation
    """
    for link in soup.findAll('link'):
        if link['type'] == 'text/css':
            css = DOMAIN + link['href']
            if css not in fileDict['cssUrls']:
                fileDict['cssUrls'].append(css)
                fileName = css[css.rfind("/") + 1:]
                if fileName.find("?") > 0:
                    fileName = fileName[:fileName.find("?")]
                fileDict['cssFileNames'].append(fileName)
                fileName = css.rfind('/')
    return fileDict


def get_img(soup, fileDict, uc):
    """
    Returns fileDict updated with addresses of D2L-created image files, like
     icons and background images, used in the formatting of a single
     presentation page. fileDict['formatImg'] list will be updated.

    Parameters:
        soup: a BeautifulSoup object created from a presentation page
        fileDict: dict of all files linked to in a presentation
    """
    for img in soup.findAll('img'):
        if img['src'].find('d2lFile') < 0:
            img = DOMAIN + img['src']
            if img not in fileDict['imgUrls']:
                fileDict['imgUrls'].append(img)
        else:
            address = DOMAIN + img['src']
            epoId = get_epo_id(img['src'])
            if epoId not in fileDict['fileIds']:
                fileDict['fileIds'].append(epoId)
                fileDict['fileUrls'].append(address)
                fileName = d2lepoexport.get_ep_object_properties(uc, epoId).\
                    FileName.strip()
                fileDict['fileNames'].append(fileName)
    return fileDict


def populate_file_dict(epObject, uc, fileDict):
    """
    Returns fileDict populated with information from all pages of an ePortfolio
     presentation.

    Parameters:
        epObject: an ePortfolio presentation object from
         d2lepoexport.get_ep_object_properties or
         d2lepoexport.get_ep_presentation.
    """
    fileDict = get_pages(epObject, fileDict)
    for url in fileDict['pageUrls']:
        soup = make_soup(url)
        fileDict = get_embedded_object(soup, fileDict, uc)
        fileDict = get_css(soup, fileDict)
        fileDict = get_img(soup, fileDict, uc)
    return fileDict


def download_presentation(epObject, uc):
    """
    Creates and populates a fileDict and downloads files it references. Creates
     a directory named after the presentation containing individual folders for
     each type of file downloaded, as outlined below:
     Presentation (includes index.html)
        |___Pages (HTML files)
        |___Content (user images, docs, and other files)
        |___Formatting (css and image files for layout and formatting)
     Returns the fileDict.

    Parameters:
        fileDict: dict of all files linked to in a presentation
    """
    fileDict = make_file_dict()
    fileDict = populate_file_dict(epObject, uc, fileDict)
    now = str(datetime.datetime.now().hour) + \
        str(datetime.datetime.now().minute) + \
        str(datetime.datetime.now().second)
    directoryName = epObject.Name.replace(" ", "") + "_presentation_" + now
    os.mkdir(directoryName)
    os.chdir(directoryName)
    temp = tempfile.TemporaryFile()
    temp.write(urllib.request.urlopen(fileDict['pageUrls'][0]).read())
    temp.seek(0)
    update_page(temp, fileDict, "index.html", index=True)
    temp.close()
    os.mkdir("Pages")
    os.chdir("Pages")
    for (pageUrl, pageFileName) in zip(fileDict['pageUrls'][1:], 
                                       fileDict['pageFileNames'][1:]):
        temp = tempfile.TemporaryFile()
        temp.write(urllib.request.urlopen(pageUrl).read())
        update_page(temp, fileDict, pageFileName)
        temp.close()
    os.chdir("../")
    os.mkdir("Content")
    os.chdir("Content")
    for (fileUrl, fileId) in zip(fileDict['fileUrls'], fileDict['fileIds']):
        fileName = d2lepoexport.get_ep_object_properties(uc, fileId).\
            FileName.strip()
        urllib.request.urlretrieve(fileUrl, fileName)
    os.chdir("../")
    os.mkdir("Formatting")
    os.chdir("Formatting")
    for (cssUrl, cssFileName) in zip(fileDict['cssUrls'],
                                  fileDict['cssFileNames']):
        temp = tempfile.TemporaryFile()
        temp.write(urllib.request.urlopen(cssUrl).read())
        temp.seek(0)
        update_css_file(cssUrl, temp, cssFileName)
        temp.close()
    for imgUrl in fileDict['imgUrls']:
        fileName = imgUrl[imgUrl.rfind("/"): ]
        if fileName.find("?") > 0:
            fileName = fileName[: fileName.find("?")]
        urllib.request.urlretrieve(imgUrl, fileName)
    os.chdir("../")
    print(str(fileDict))
    return fileDict


def write_page(soup, fileName):
    """
    Writes a BeautifulSoup object to an html file.

    Parameters:
        soup: BeautifulSoup object
        fileName: name of the file as a string
    """
    soup.prettify(formatter='html')

    with open(fileName, 'wb') as f:
        f.write(str(soup).encode('utf-8'))


##########################
# Functions to edit html #
##########################


def update_page(temp, fileDict, fileName, index=False):
    """
    Updates the links in an html file to match the new file locations.

    Parameters:
        temp: tempfile object
        fileDict: dict of all files linked to in a presentation
        index: list index of page to be processed
    """
    temp.seek(0)
    soup = BeautifulSoup(temp.read())
    update_file_urls(soup, fileDict, index)
    update_css_urls(soup, fileDict, index)
    update_image_urls(soup, fileDict, index)
    update_page_urls(soup, fileDict, index)
    strip_script(soup)
    write_page(soup, fileName)


def update_file_urls(soup, fileDict, index=False):
    """
    Updates links to ePortfolio objects embedded in a presentation page.

    Parameters:
        soup: BeautifulSoup object
        fileDict: dict of all files linked to in a presentation
    """
    for item in soup.find_all(['a', 'img']):
        for (fileId, fileName) in zip(fileDict['fileIds'],
                                      fileDict['fileNames']):
            if item.has_attr('href') and item['href'].find(fileId) > 0:
                if index == True:
                    item['href'] = './content/' + fileName
                else:
                    item['href'] = '../content/' + fileName
            if item.has_attr('src') and item['src'].find(fileId) > 0:
                if index == True:
                    item['src'] = './content/' + fileName
                else:
                    item['src'] = '../content/' + fileName


def update_css_urls(soup, fileDict, index=False):
    """
    Updates links to css files in a presentation page.

    Parameters:
        soup: BeautifulSoup object
        fileDict: dict of all files linked to in a presentation
    """
    for a in soup.find_all('link', {'type': 'text/css'}):
        for (cssUrl, cssFileName) in zip(fileDict['cssUrls'],
                                         fileDict['cssFileNames']):
            if cssUrl.find(a['href']) > 0:
            #if a['href'] == urllib.parse.urlparse(cssUrl).path:
                if index == True:
                    a['href'] = './formatting/' + cssFileName
                else:
                    a['href'] = '../formatting/' + cssFileName


def update_image_urls(soup, fileDict, index=False):
    """
    Updates links to image files used in formatting a presentation.

    Parameters:
        soup: BeautifulSoup object
        fileDict: dict of all files linked to in a presentation
    """
    for img in soup.find_all('img'):
        for (imgUrl, imgFileName) in zip(fileDict['imgUrls'],
                                         fileDict['imgFileNames']):
            if img['src'].find('d2lFile') < 0:
                if img['src'] == urllib.parse.urlparse(imgUrl).path:
                    if index == True:
                        img['src'] = './formatting/' + imgFileName
                    else:
                        img['src'] = '../formatting/' + imgFileName


def update_page_urls(soup, fileDict, index=False):
    """
    Updates links to other pages in a presentation.

    Parameters:
        soup: BeautifulSoup object
        fileDict: dict of all files linked to in a presentation
    """
    for div in soup.find_all('div', {'class': "d_t_nav_current_page"}):
        div.contents[0]['href'] = "#"
    for a in soup.find_all('a', {'href': 'javascript://'}):
        for (pageId, pageFileName) in zip(fileDict['pageIds'],
                                           fileDict['pageFileNames']):
            if a['onclick'].find(str(pageId)) > 0:
                if index == True:
                    a['href'] = './pages/' + pageFileName
                elif (index == False) and (pageFileName != 'index.html'):
                    a['href'] = pageFileName
                else:
                    a['href'] = '../' + pageFileName

def strip_script(soup):
    """
    Removes all script tags from a presentation page.

    Parameters:
        soup: BeautifulSoup object
    """
    for script in soup.find_all('script'):
        soup.script.decompose()


#########################
# Functions to edit css #
#########################


def update_css_file(cssUrl, temp, fileName):
    """
    Updates the links in CSS files and downloads the files linked.

    Parameters:
        temp: css file as a tempfile.TemporaryFile object
        fileName: name of the css file
    """
    with open(fileName, 'wb') as f:
        for line in temp:
            contains_link = line.find(b"url(")
            if contains_link != -1:
                beginIndex = contains_link + 4
                endIndex = line.find(b")", beginIndex)
                url = line[beginIndex: endIndex].decode()
                if url[0] == "/":
                    address = DOMAIN + url
                elif url[0].isalnum():
                    url = "/" + url
                    address = cssUrl[: cssUrl.rfind("/")] + url
                else:
                    count = 0
                    while url[count] != "/":
                        count += 1
                    address = DOMAIN + url[count:]
                    while not address[-1].isalnum():
                        address = address[: -1]
                newAddress = address[address.rfind("/") + 1:]
                if newAddress.find("?") > 0:
                    newAddress = newAddress[: newAddress.find("?")]
                try:
                    urllib.request.urlretrieve(address, newAddress)
                except urllib.error.HTTPError:
                    print(urllib.error.HTTPError)
                line = (line[:beginIndex].decode() + newAddress + line[endIndex:].decode()).encode('UTF-8')
            f.write(line)
