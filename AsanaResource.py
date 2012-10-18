import ConfigParser
import requests
import datetime

try:
    import simplejson as json
except ImportError:
    import json
from pprint import pprint

class AsanaError(Exception): pass

class AsanaResource(object):
    def __init__(self): #pass location of config file 
        self.asana_url = "https://app.asana.com/api"
        self.api_version = "1.0"
        self.aurl = "/".join([self.asana_url, self.api_version])

        # TODO: right place for this?
        config = ConfigParser.ConfigParser()
        config.read('asana.cfg')
        config_section = 'Asana Configuration'

        self.api_key = config.get(config_section, 'api_key')
        self.debug = config.getboolean(config_section, 'debug')

    @property
    def resource(self):
        return self.resource

    def _utcstr_to_datetime(self, timestamp):
        """Convert a UTC formatted string to a datetime object.

        Args:
            timestamp (str): UTC formatted str (e.g. '2012-02-22T02:06:58.147Z')
        """
        timestamp = timestamp.replace('T', ' ').replace('Z', '')
        return datetime.datetime.strptime(timestamp, '%Y-%m-%d %H:%M:%S.%f')

    # TODO: r.json

    def _check_http_status(self, r):
        """Check the status code. Raise an exception if there's an error with
        the status code and message.

        Args:
            r (request obj): request object
        """
        sc = r.status_code
        if sc == 200 or sc == 201:
            return

        error_message = json.loads(r.text)['errors'][0]['message']
        if sc in [400, 401, 403, 404, 429]:
            raise Exception('Error: HTTP Status %s: %s' %
                            (r.status_code, error_message))
        elif sc == 500:
            phrase = json.loads(r.text)['errors'][0]['phrase']
            raise Exception('HTTP Status %s: %s (phrase: %s)' %
                            (r.status_code, error_message, ph))

    def _handle_response(self, r):
        """Check the headers. If there is an error raise an Exception,
        otherwise return the data.

        Args:
            r (request obj): request object to check headers of

        Returns:
            dict: json response from Asana
        """
        if r.headers['content-type'].split(';')[0] == 'application/json':
            return json.loads(r.text)['data']
        else:
            raise Exception('Did not receive json from api: %s' % str(r))    

    def get(self, endpoint="", use_resource=True):
        """Submits a get to the Asana API and returns the result. If
        use_resource is true, use the resource property and the endpoint
        argument to construct the API endpoint, otherwise use the just
        the endpoint.

        Returns:
            dict: json response from Asana
        """
        if use_resource:
            target = "/".join([self.aurl, self.resource, str(endpoint)])
        else:
            target = "/".join([self.aurl, str(endpoint)])

        if self.debug:
            print "-> Calling: %s" % target

        r = requests.get(target, auth=(self.api_key, ""))
        self._check_http_status(r)
        return self._handle_response(r)  

    def post(self, endpoint="", data=""): #TODO bad?
        """Submits a post to the Asana API and returns the result.

        Args:
            api_target (str): Asana API endpoint TODO
            data (dict): post data

        Returns:
            dict: json response from Asana
        """
        target = "/".join([self.aurl, self.resource, str(endpoint)])
        if self.debug:
            print "-> Posting to: %s" % target
            print "-> Post payload:"
            pprint(data)

        r = requests.post(target, auth=(self.api_key, ""), data=data)
        self._check_http_status(r)
        return self._handle_response(r)

    def put(self, endpoint, data):
        """Submits a put to the Asana API and returns the result.

        Args:
            api_target (str): Asana API endpoint
            data (dict): post data

        Returns:
            dict: json response from Asana
        """
        target = "/".join([self.aurl, self.resource, str(endpoint)])
        if self.debug:
            print "-> Putting to: %s" % target
            print "-> Put payload:"
            pprint(data)

        r = requests.put(target, auth=(self.api_key, ""), data=data)
        self._check_http_status(r)
        return self._handle_response(r)

class Users(AsanaResource):
    def __init__(self, workspace_id=None):
        super(Users, self).__init__()

        # If a workspace is specified, we must use a different resource
        # as required by the API spec.
        if workspace_id:
            endpoint = 'workspaces/%s' % workspace_id
            jr = self.get(endpoint=endpoint, use_resource=False)
        else:
            jr = self.get()

        self._users = [User(elt['id']) for elt in jr]

    users = property(lambda self: self._users)

    @property
    def resource(self):
        return 'users'

class User(AsanaResource):
    def __init__(self, user_id='me'):
        super(User, self).__init__()
        jr = self.get(user_id)
        self._name = jr['name']
        self._email = jr['email']
        self._id = jr['id']

    id = property(lambda self: self._id)
    name = property(lambda self: self._name)
    email = property(lambda self: self._email)

    @property
    def resource(self):
        return 'users'

    @property
    def workspaces(self):
        jr = self.get(self._id)
        return [Workspace(elt['id']) for elt in jr]

class Task(AsanaResource):
    def __init__(self,
                 task_id=None, 
                 workspace_id=None,
                 **kwargs):
        super(Task, self).__init__()

        if task_id and workspace_id:
            raise AsanaError('Bad arguments') #TODO more revealing error
        elif task_id and kwargs:
            raise AsanaError('Bad arguments')

        if task_id:
            jr = self.get(task_id)
        elif workspace_id:
            merged_post_params = dict([('workspace', workspace_id)] +
                                      kwargs.items())
            jr = self.post(data=merged_post_params)

        date_frmtr = lambda d: self._utcstr_to_datetime(d) if d else None

        self._id = jr['id']
        self._name = jr['name']
        self._notes = jr['notes']
        self._assignee_status = jr['assignee_status']
        self._created_at = self._utcstr_to_datetime(jr['created_at'])
        self._modified_at = self._utcstr_to_datetime(jr['modified_at'])
        self._completed_at = date_frmtr(jr['completed_at'])
        self._completed = jr['completed']
        self._due_on = jr['due_on']
        self._tags = jr['tags']
        self._projects = jr['projects']

    id = property(lambda self: self._id)
    name = property(lambda self: self._name)
    notes = property(lambda self: self._notes)
    created_at = property(lambda self: self._created_at)
    modified_at = property(lambda self: self._modified_at)
    completed_at = property(lambda self: self._completed_at)
    completed = property(lambda self: self._completed)
    assignee_status = property(lambda self: self._assignee_status)

    @property
    def resource(self):
        return 'tasks'

    @property
    def parent(self): # TODO
        jr = self.get(self._id)
        if jr['parent']:
            return User(jr['parent']['id'])
        else:
            return None

    @property
    def workspace(self):
        jr = self.get(self._id)
        return Workspace(jr['workspace']['id'])

    @property
    def assignee(self):
        jr = self.get(self._id)
        if jr['assignee']:
            return User(jr['assignee']['id'])
        else:
            return None

    @property
    def followers(self):
        jr = self.get(self._id)
        if jr['followers']:
            return [User(elt['id']) for elt in jr['followers']]
        else:
            return []

    @property
    def projects(self):
        jr = self.get(self._id)
        if jr['projects']:
            return [Project(elt['id']) for elt in jr['projects']]
        else:
            return []

    @property
    def tags(self):
        jr = self.get('%s/tags' % self._id)
        if jr:
            return [Tag(elt['id']) for elt in jr]
        else:
            return []

    @assignee.setter
    def assignee(self, user):
        try:
            user_id = user.id
        except AttributeError: 
            raise AsanaError("Requires a User object.", user)

        self.put(self._id, {'assignee': user_id})
        self.assignee = user # TODO: deepcopy?

    @assignee_status.setter
    def assignee_status(self, status):
        ok_status = ['upcoming', 'inbox', 'later', 'today', 'upcoming']
        if status not in ok_status:
            s = ','.join(ok_status)
            raise AsanaError('Status must be one of the following:' + s)

        self.put(self._id, {'status': status})
        self._assignee_status = status

    @name.setter
    def name(self, name):
        self.put(self._id, {'name': name})
        self._name = name

    @notes.setter
    def notes(self, notes):
        self.put(self._id, {'notes': notes})
        self._notes = notes

    @completed.setter
    def completed(self, status):
        if not isinstance(status, bool): #TODO: idiomatic?
            raise AsanaError("Assignment must be of type bool")

        self.put(self._id, {'completed': completed}) # TODO: check if completed needs to be json'd
        self._status = status

    def add_tag(self, tag):
        if isinstance(tag, int) or isinstance(tag, str):
            self.post('%d/addTag' % tag, {'tag': tag})
            self._tags.append(Tag(tag))
        elif isinstance(tag, Tag):
            self.post('%d/addTag' % tag, {'tag': tag.id})
            self._tags.append(tag)
        else:
            raise AsanaError("Requires a int, str, or Tag object")

    def _remove_tag_helper(self, tag_id, arr):
        self._tags = filter(lambda x: True if x.id == tag_id else False, arr)

    def remove_tag(self, tag):
        if isinstance(tag, int) or isinstance(tag, str):
            self.post('%d/removeTag' % tag, {'tag': tag})
            _remove_tag_helper(int(tag), self._tags)
        elif isinstance(tag, Tag):
            self.post('%d/removeTag' % tag.id, {'tag': tag.id})
            _remove_tag_helper(tag.id, self._tags)
        else:
            raise AsanaError("Requires a int, str, or Tag object")

    def bulk_update(self, **kwargs):
        payload = {}
        pass

class Workspace(AsanaResource):
    def __init__(self, workspace_id):
        super(Workspace, self).__init__()
        jr = self.get(workspace_id)
        self._id = jr['id']
        self._name = jr['name']

    id = property(lambda self: self._id)
    name = property(lambda self: self._name)

    @property
    def resource(self):
        return 'workspaces'

    @name.setter
    def name(self, name):
        self.put(self._id, {'name': name})
        self._name = name

class Tag(AsanaResource):
    def __init__(self, workspace_id=None, name=None, tag_id=None):
        super(Tag, self).__init__()

        # Create a tag, or return an existing tag. The constructor parameters
        # specifically determine what is allowable
        if workspace_id and name and not tag_id:
            jr = self.post(data={'workspace': workspace_id, 'name': name})
        elif tag_id and not workspace_id and not name:
            jr = self.get(tag_id)
        else:
            raise AsanaError("Bad Arguments")

        self._id = jr['id']
        self._name = jr['name']
        self._notes = jr['notes']
        self._created_at = self._utcstr_to_datetime(jr['created_at'])

    # Concisely define trivial getters
    id = property(lambda self: self._id)
    name = property(lambda self: self._name)
    notes = property(lambda self: self._notes)
    workspace = property(lambda self: self._workspace)
    created_at = property(lambda self: self._created_at)

    @property
    def resource(self):
        return 'tags'

    @property
    def followers(self):
        """Return a list of all Users following this Tag"""
        jr = self.get(self._id)
        return [User(elt['id']) for elt in jr['followers']]

    @property
    def tasks(self):
        """Return a list of all Tasks objects associated with this tag"""
        jr = self.get("/".join([self._id, 'tasks']))
        return [Tag(elt['id'] for elt in jr['tasks'])]

    @name.setter
    def name(self, name):
        self.put(self._id, {'name': name})
        self._name = name

    @notes.setter
    def notes(self, notes):
        self.put(self._id, {'notes': notes})
        self._notes = notes

#u = User()
#User.users()
#u.users()
# ws = u.workspaces()
# import pdb
# pdb.set_trace()
# # u.all_users()
# w = Workspace(151953184165)
# w.name = 'EECS'

import pdb
pdb.set_trace()
task = Task(workspace_id=151953184165)
print task.id

# t = Tag(workspace_id=151953184165, name='yolo')
# print t.id
# print t.followers
# print t.notes
# t.notes = "lolol"
# print t.notes

