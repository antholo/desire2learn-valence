"""
Provides functions for retrieving information from D2L Valence ePortfolio and
support for handling ePortfolio data structures. This code does not support
uploading to ePortfolio.
"""
from xml.etree.ElementTree import Element, tostring
import xml.dom.minidom
# d2lvalence_util.data to build on abstract D2L structures
import data as d2l_data
# d2lvalence_util.service to build on abstract D2L functions
import service as d2l_service
import d2lepoexport_presentation

##############
# Constants  #
##############

# ObjectTypeId constants
EPOBJ_T = {
    'ep_object': 0,
    'collection': 100,
    'static_collection': 110,
    'dynamic_collection': 120,
    'reflection': 200,
    'artifact': 300,
    'file_artifact': 310,
    'form_artifact': 320,
    'le_artifact': 330,
    'le_competency_artifact': 331,
    'le_grade_artifact': 332,
    'le_quiz_artifact': 333,
    'le_dropbox_artifact': 334,
    'url_artifact': 340,
    'presentation': 400,
    'learning_objective': 600, }

# Rights that EP users can be granted on an EP object shared to them
OBJRIGHT_T = {
    'View': 1,
    'SeeComments': 2,
    'AddComments': 3,
    'ViewAssessments': 4,
    'AddAssessments': 5,
    'Edit': 6, }

##############
# Structures #
##############


def dict_to_xml(tag, d):
    """
    Turn a simple dict of key/value pairs into XML.

    From Python Cookbook, 3rd edition, by David Beazley and Brian K. Jones
     (O'Reilly). 978-1-449-34037-7.
    Permission was not required for use. See "Using Code Samples" at:
    http://chimera.labs.oreilly.com/books/1230000000393/pr01.html
    """
    elem = Element(tag)
    for key, val in d.items():
        child = Element(key)
        child.text = str(val)
        elem.append(child)
    return elem


class epObject(d2l_data.D2LStructure):
    """
    Structure of ePortfolio object properties returned from D2L.
    """
    def __init__(self, json_dict):
        d2l_data.D2LStructure.__init__(self, json_dict)

    ObjectId = property(d2l_data._get_number_prop('ObjectId'))
    Name = property(d2l_data._get_string_prop('Name'))
    Description = property(d2l_data._get_string_prop('Description'))
    AllowComments = property(d2l_data._get_boolean_prop('AllowComments'))
    UserId = property(d2l_data._get_number_prop('UserId'))
    ObjectTypeId = property(d2l_data._get_number_prop('ObjectTypeId'))
    ViewLink = property(d2l_data._get_string_prop('ViewLink'))
    CommentsCount = property(d2l_data._get_number_prop('CommentsCount'))
    HasUnreadComments = property(d2l_data._get_boolean_prop(
        'HasUnreadComments'))
    Created = property(d2l_data._get_string_prop('Created'))
    Modified = property(d2l_data._get_string_prop('Modified'))

    @property
    def GeoTag(self):
        return self.props['GeoTag']

    @property
    def Tags(self):
        return self.props['Tags']

    @Tags.setter
    def Tags(self, new_tags_list):
        self.props['Tags'] = new_tags_list

    @property
    def Comments(self):
        return self.props['Comments']

    @property
    def Permissions(self):
        return self.props['Permissions']

    def descriptive_object_type_id(self):
        """Return text labels for this instance's ObjectTypeId"""
        for (k, v) in EPOBJ_T.items():
            if v == self.ObjectTypeId:
                return k

    def descriptive_permissions(self):
        """Return list of text labels for this instance's Permssions list"""
        perm_list = []
        for permission in self.Permissions:
            for (k, v) in OBJRIGHT_T.items():
                if v == permission:
                    perm_list.append(k)
        return perm_list


class epFileArtifact(epObject):
    """
    Structure for ePortfolio File Artifacts, which add these properties to
    ePortfolio objects:
        Extension: string containing file extension (ex: '.pdf' or '.jpg')
        FileName: string containing name of file and extension (ex: 'data.py')
        FileSize: int size of the file (in bytes)
        UploadKey: provided by service for use in uploading to attach metadata
         to files.
    """
    def __init__(self, json_dict):
        epObject.__init__(self, json_dict)

    Extension = property(d2l_data._get_string_prop('Extension'))
    FileName = property(d2l_data._get_string_prop('FileName'))
    FileSize = property(d2l_data._get_number_prop('FileSize'))
    UploadKey = property(d2l_data._get_string_prop('UploadKey'))


class epUrlArtifact(epObject):
    """
    Structure for ePortfolio URL Artifacts, which adds one property to
     ePortfolio object properties:
        Url: string containing the address linked to by the artifact?
    """
    def __init__(self, json_dict):
        epObject.__init__(self, json_dict)

    Url = property(d2l_data._get_string_prop('Url'))


class epCollection(epObject):
    """
    Structure for ePortfolio Collection objects. It adds one property to
     ePortfolio object properties:
        ItemsCount: int indicating number of items in the collection
    """
    def __init__(self, json_dict):
        epObject.__init__(self, json_dict)

    ItemsCount = property(d2l_data._get_number_prop('ItemsCount'))

    @property
    def ItemIds(self):
        return self.props['ItemIds']

    @property
    def Items(self):
        return self.props['Items']


class epPresentation(epObject):
    """
    Structure for ePortfolio Presentation objects. It adds three properties to
     ePortfolio object properties:
        BannerTitle: string containing the presentation's banner title
        BannerDescription: string containin the presentation's banner
         description
    """
    def __init__(self, json_dict):
        epObject.__init__(self, json_dict)

    BannerTitle = property(d2l_data._get_string_prop('BannerTitle'))
    BannerDescription = property(d2l_data._get_string_prop(
                                 'BannerDescription'))


#############
# Functions #
#############


def get_ep_object_properties(uc,
                             object_id,
                             ver='2.3',
                             c=False,
                             **kwargs):
    """
    Return an ePortfolio object by ID. Checks whether this is a specific type
    of ePortfolio object and return appropriate data corresponding to type.

    Parameters:
        uc: user context, from d2lvalence.auth.fashion_user_context
        object_id: an ePortfolio object's unique identifier
        ver (optional): ePortfolio API version as a String
        c (optional): include comments attached to object if true
    """
    kwargs.setdefault('params', {})
    if c:
        kwargs['params'].update({'c': c})
    route = '/d2l/api/eP/{0}/object/{1}'.format(ver, object_id)
    # Gets generic ePortfolio object properties
    r = d2l_service._get(route, uc, **kwargs)

    # Gets specific object properties for unique epObject types
    if r['ObjectTypeId'] == EPOBJ_T.get('file_artifact'):
        return get_ep_file_artifact(uc, object_id, ver, c, **kwargs)

    elif r['ObjectTypeId'] == EPOBJ_T.get('url_artifact'):
        return get_ep_url_artifact(uc, object_id, ver, c, **kwargs)

    elif r['ObjectTypeId'] == EPOBJ_T.get('collection'):
        return get_ep_collection(uc, object_id, ver, c, **kwargs)

    elif r['ObjectTypeId'] == EPOBJ_T.get('presentation'):
        return get_ep_presentation(uc, object_id, ver, c, **kwargs)

    else:
        return epObject(r)


def get_ep_object(uc,
                  object_id,
                  ver='2.3',
                  c=False,
                  **kwargs):
    """
    Return an ePortfolio object by ID.

    Parameters:
        uc: user context, from d2lvalence.auth.fashion_user_context
        object_id: an ePortfolio object's unique identifier
        ver (optional): ePortfolio API version as a String
        c (optional): include comments attached to object if true
    """
    kwargs.setdefault('params', {})
    if c:
        kwargs['params'].update({'c': c})
    route = '/d2l/api/eP/{0}/object/{1}'.format(ver, object_id)
    r = d2l_service._get(route, uc, **kwargs)
    return epObject(r)


def get_ep_file_artifact(uc,
                         object_id,
                         ver='2.3',
                         c=False,
                         **kwargs):
    """
    Return an ePortfolio file artifact by ID.

    Parameters:
        uc: user context, from d2lvalence.auth.fashion_user_context
        object_id: an ePortfolio object's unique identifier
        ver (optional): ePortfolio API version as a String
        c (optional): include comments attached to object if true
    """
    kwargs.setdefault('params', {})
    if c:
        kwargs['params'].update({'c': c})
    route = '/d2l/api/eP/{0}/artifact/file/{1}'.format(ver, object_id)
    r = d2l_service._get(route, uc, **kwargs)
    return epFileArtifact(r)


def get_ep_url_artifact(uc,
                        object_id,
                        ver='2.3',
                        c=False,
                        **kwargs):
    """
    Return an ePortfolio url artifact by ID.

    Parameters:
        uc: user context, from d2lvalence.auth.fashion_user_context
        object_id: an ePortfolio object's unique identifier
        ver (optional): ePortfolio API version as a String
        c (optional): include comments attached to object if true
    """
    kwargs.setdefault('params', {})
    if c:
        kwargs['params'].update({'c': c})
    route = '/d2l/api/eP/{0}/artifact/link/{1}'.format(ver, object_id)
    r = d2l_service._get(route, uc, **kwargs)
    return epUrlArtifact(r)


def get_ep_collection(uc,
                      object_id,
                      ver='2.3',
                      c=False,
                      **kwargs):
    """
    Return an ePortfolio presentation by ID.

    Parameters:
        uc: user context, from d2lvalence.auth.fashion_user_context
        object_id: an ePortfolio object's unique identifier
        ver (optional): ePortfolio API version as a String
        c (optional): include comments attached to object if true
    """
    kwargs.setdefault('params', {})
    if c:
        kwargs['params'].update({'c': c})
    route = '/d2l/api/eP/{0}/collection/{1}/contents/'.format(ver,
                                                              object_id)
    r = d2l_service._get(route, uc, **kwargs)
    return epCollection(r)


def get_ep_presentation(uc,
                        object_id,
                        ver='2.3',
                        c=False,
                        **kwargs):
    """
    Return an ePortfolio presentation by ID.

    Parameters:
        uc: user context, from d2lvalence.auth.fashion_user_context
        object_id: an ePortfolio object's unique identifier
        ver (optional): ePortfolio API version as a String
        c (optional): include comments attached to object if true
    """
    kwargs.setdefault('params', {})
    if c:
        kwargs['params'].update({'c': c})
    route = '/d2l/api/eP/{0}/presentation/{1}'.format(ver, object_id)
    r = d2l_service._get(route, uc, **kwargs)
    return epPresentation(r)


def get_ep_object_content(uc,
                          object_id,
                          ver='2.3',
                          **kwargs):
    """
    Return the associated file(s) of an ePortfolio object as a file stream.

    Parameters:
        uc: user context, from d2lvalence.auth.fashion_user_context
        object_id: an ePortfolio object's unique identifier
        ver (optional): ePortfolio API version as a String
    """
    route = '/d2l/api/eP/{0}/object/{1}/content'.format(ver, object_id)
    return d2l_service._get(route, uc, **kwargs)


def get_ep_comment(uc,
                   object_id,
                   ver='2.3',
                   **kwargs):
    """
    Return the comments for an ePortfolio object identified by its ID.

    Parameters:
        uc: user context, from d2lvalence.auth.fashion_user_context
        object_id: an ePortfolio object's unique identifier
        ver (optional): ePortfolio API version as a String

    Return data includes two properties:

    PagingInfo: dict containing:
        Bookmark: number (int) of last item of PagedResultSet returned for
         passing to get remaining items in PagedResultSet
        HasMoreItems: boolean,  True if more items in PagedResultSet to return

    Items: list containing dictionaries of the following properties for each
     comment:
        ObjectId: unique int ePortfolio identifier
        CommentId: unique int ePortfolio comment identifier
        UserId: unique int D2L user identifier
        CreatedDate: string containing creation date of comment
        Body: string containing the comment body in HTML
    """
    route = '/d2l/api/eP/{0}/object/{1}/comments/'.format(ver, object_id)
    r = d2l_service._get(route, uc, **kwargs)
    return d2l_data.PagedResultSet(r)


def get_ep_tag(uc,
               object_id,
               ver='2.3',
               **kwargs):
    """
    Return the tags for an ePortfolio object identified by its ID.

    Parameters:
        uc: user context, from d2lvalence.auth.fashion_user_context
        object_id: an ePortfolio object's unique identifier
        ver (optional): ePortfolio API version as a String

    Return data is a list of dictionaries. Each dictionary contains:
        Type: int value 0 for public tags, 1 for private tags
        Text: string containing tag text
    """
    route = '/d2l/api/eP/{0}/object/{1}/tags/'.format(ver, object_id)
    r = d2l_service._get(route, uc, **kwargs)
    return r


def get_ep_objects(uc,
                   ver='2.3',
                   c=False,
                   q='',
                   bookmark='',
                   pagesize=None,
                   **kwargs):
    """
    Return all ePortfolio objects owned by the current user context.

    Parameters:
        uc: user context, from d2lvalence.auth.fashion_user_context
        ver (optional): ePortfolio API version as a String
        c (optional): set to True to include comments
        q (optional): query filter expression as a String to filter results,
         (docs.valence.desire2learn.com/res/epobject.html#object-query-filters)
        bookmark (optional): ObjectId of last item in data segment, passed to
         start the next data segment with the following ObjectId
        pagesize (optional): int number of entries to return per data segment

    Return data includes two properties:
    PagingInfo (dict):
        Bookmark: number (int) of last item of PagedResultSet returned for
         passing to get remaining items in PagedResultSet
        HasMoreItems: boolean,  True if more items in PagedResultSet to return
    Items: list containing all of the relevant ePortfolio object properties
     for each item.
    """
    route = '/d2l/api/eP/{0}/objects/my/'.format(ver)
    kwargs.setdefault('params', {})
    if c:
        kwargs['params'].update({'c': c})
    if q:
        kwargs['params'].update({'q': q})
    if bookmark:
        kwargs['params'].update({'bookmark': bookmark})
    if pagesize:
        kwargs['params'].update({'pagesize': pagesize})
    r = d2l_service._get(route, uc, **kwargs)
    return d2l_data.PagedResultSet(r)


##############
# PROCESSING #
##############


def get_ep_properties_as_xml(uc, object_id, ver='2.3', c=False, **kwargs):
    """
    Returns an ePortfolio object's properties formatted in XML.

    Parameters:
        uc: user context, from d2lvalence.auth.fashion_user_context
        object_id: an ePortfolio object's unique identifier
        ver (optional): ePortfolio API version as a String
        c (optional): include comments attached to object if true
    """
    obj_props = get_ep_object_properties(uc, object_id, ver, c, **kwargs)
    xml_element = Element(obj_props.descriptive_object_type_id())
    for (key, val) in obj_props.as_dict().items():
        if c:
            if key == 'Comments':
                comment_section = Element('Comments')
                for comment in val:
                    comment_element = dict_to_xml('Comment', comment)
                    comment_section.append(comment_element)
                xml_element.append(comment_section)
        elif key == 'Tags':
            if val is not None:
                tag_section = Element('Tags')
                for tag in val:
                    tag_element = dict_to_xml('Tag', tag)
                    tag_section.append(tag_element)
                xml_element.append(tag_section)
        elif key == 'Permissions':
            perms_element = Element('Permissions')
            perms = []
            for permission_code in val:
                for (k, v) in OBJRIGHT_T.items():
                    if v == permission_code:
                        perms.append(k)
            perms_element.text = str(perms)
            xml_element.append(perms_element)
        else:
            child = Element(key)
            child.text = str(val)
            xml_element.append(child)
    return xml_element


def get_ep_object_metadata(uc, object_id, ver='2.3', c=False, **kwargs):
    """
    Downloads an ePortfolio object's properties into a .txt file.

    Parameters:
        uc: user context, from d2lvalence.auth.fashion_user_context
        object_id: an ePortfolio object's unique identifier
        ver (optional): ePortfolio API version as a String
        c (optional): include comments attached to object if true
    """
    metadata = get_ep_object_properties(uc, object_id, ver, c, **kwargs)
    with open(metadata.Name + "_metadata.txt", 'wb+') as download:
        download.write(str(metadata).encode('utf-8'))


def get_ep_object_metadata_xml(uc, object_id, ver='2.3', c=False, **kwargs):
    """
    Downloads an ePortfolio object's properties into a .xml file.

    Parameters:
        uc: user context, from d2lvalence.auth.fashion_user_context
        object_id: an ePortfolio object's unique identifier
        ver (optional): ePortfolio API version as a String
        c (optional): include comments attached to object if true
    """
    metadata = get_ep_properties_as_xml(uc, object_id, ver, c, **kwargs)
    filename = str(tostring(metadata.find('Name')))[8:-8]
    with open(filename + "_metadata.xml", 'w+') as download:
        with xml.dom.minidom.parseString(tostring(metadata,
                                                  encoding='utf-8'))as dom:
            dom.writexml(download, addindent="\t", newl="\n")


def get_ep_object_with_metadata(uc, object_id, ver='2.3', c=False, xml=False,
                                **kwargs):
    """
    Downloads an ePortfolio object and a .txt file of ePortfolio object
    properties.

    Parameters:
        uc: user context, from d2lvalence.auth.fashion_user_context
        object_id: an ePortfolio object's unique identifier
        ver (optional): ePortfolio API version as a String
        c (optional): include comments attached to object if true
    """
    if xml:
        get_ep_object_metadata_xml(uc, object_id, ver, c, **kwargs)
    else:
        get_ep_object_metadata(uc, object_id, ver, c, **kwargs)

    metadata = get_ep_object_properties(uc, object_id, ver, c, **kwargs)
    type = metadata.ObjectTypeId

    if type == EPOBJ_T.get('file_artifact'):
        download_stream = get_ep_object_content(uc, object_id, ver, **kwargs)
        with open(metadata.FileName, 'wb+') as file:
            file.write(download_stream)

    elif type == EPOBJ_T.get('url_artifact'):
        with open(metadata.Name + ".txt", 'w+') as file:
            file.write(metadata.Name + "\n")
            file.write(metadata.Url + "\n")
            file.write(metadata.Description)

    elif type == EPOBJ_T.get('collection'):
        for item_id in metadata.ItemIds:
            get_ep_object_with_metadata(uc, item_id, ver, c, xml, **kwargs)

    elif type == EPOBJ_T.get('presentation'):
        d2lepoexport_presentation.download_presentation(metadata, uc)

    else:
        with open(metadata.Name + ".txt", 'w+') as file:
            file.write(metadata.Name + "\n")
            file.write(metadata.Description)


# function to download all content with metadata
