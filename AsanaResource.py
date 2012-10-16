import ConfigParser
import requests
import datetime

try:
    import simplejson as json
except ImportError:
    import json
from pprint import pprint

class AsanaResource(object):
    def __init__(self):
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

    def get(self, endpoint=""):
        """Submits a get to the Asana API and returns the result.

        Returns:
            dict: json response from Asana
        """
        target = "/".join([self.aurl, self.resource, str(endpoint)])
        if self.debug:
            print "-> Calling: %s" % target

        r = requests.get(target, auth=(self.api_key, ""))
        self._check_http_status(r)
        return self._handle_response(r)  

    def post(self, data, endpoint=""): #TODO bad?
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

class User(AsanaResource):
    def __init__(self, user_id='me'):
        super(User, self).__init__()

        user_json = self.get(user_id)
        self._name = user_json['name']
        self._email = user_json['email']
        self._id = user_json['id']
        self._workspaces = user_json['workspaces']

    @classmethod
    def users(cls):
        import pdb
        pdb.set_trace()
        users = []
        users_json = cls.get()
        for user_dict in users_json:
            users.append(User(str(user_dict['id'])))

        return users

    @property
    def resource(self):
        return 'users'

    @property
    def email(self):
        return self._email

    @property
    def name(self):
        return self._name

    @property
    def id(self):
        return self._id

    # problem with returning reference? dangerous?
    # static?
    @property
    def workspaces(self):
        self._workspaces = [Workspace(elt['id']) for elt in self._workspaces]
        return self._workspaces

class Task(AsanaResource):
    def __init__(self, workspace_id):
        super(Tasks, self).__init__()
        # cast completed to true/false

    @property
    def resource(self):
        return 'tasks'

    @property
    def created_at(self):
        return self._created_at

    @property
    def completed_at(self):
        return self._completed_at

    @property
    def modified_at(self):
        return self._modified_at

    @property
    def followers(self):
        self._followers = [User(elt['id']) for elt in self._followers]
        return self._followers

    @property
    def projects(self):
        self._projects = [Project(elt['id']) for elt in self._projects]
        return self._projects

    @property
    def workspace(self):
        self._workspace = Workspace(self._workspace['id'])
        return self._workspace

    @property
    def assignee(self):
        if self._assignee:
            _assignee = User(self.assignee['id'])
        return _assignee

    @assignee.setter
    def assignee(self, user):
        if type(user) != User:
            raise Exception("Requires a User object.")
        _assignee = user

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, name):
        self.put(self._id, {'name': name})
        self._name = name

    @property
    def notes(self):
        return self._notes

    @notes.setter
    def notes(self, notes):
        self.put(self._id, {'notes': notes})
        self._notes = notes

    @property
    def completed(self):
        return self.completed

    @completed.setter
    def completed(self):
        # TODO error checking


class Workspace(AsanaResource):
    def __init__(self, workspace_id):
        super(Workspace, self).__init__()
        json_resp = self.get(workspace_id)
        self._id = json_resp['id']
        self._name = json_resp['name']

    @property
    def resource(self):
        return 'workspaces'

    @property
    def id(self):
        return self._id

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, name):
        self.put(self._id, {'name': name})
        self._name = name

class Tag(AsanaResource):
    def __init__(self, workspace_id=None, name=None, tag_id=None):
        super(Tag, self).__init__()

        # Create a tag, or return an existing tag
        if workspace_id and name:
            json_resp = self.post({'workspace': workspace_id, 'name': name})
        elif tag_id:
            json_resp = self.get(tag_id)
        else:
            raise Exception("Bad constructor arguments.")

        self._id = json_resp['id']
        self._name = json_resp['name']
        self._notes = json_resp['notes']
        self._followers = json_resp['followers']
        self._workspace = json_resp['workspace']
        self._created_at = self._utcstr_to_datetime(json_resp['created_at'])

    @property
    def resource(self):
        return 'tags'

    @property
    def id(self):
        return self._id

    @property
    def created_at(self):
        return self._created_at

    @property
    def followers(self):
        self._followers = [User(elt['id']) for elt in self._followers]
        return self._followers

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, name):
        self.put(self._id, {'name': name})
        self._name = name

    @property
    def notes(self):
        return self._notes

    @notes.setter
    def notes(self, notes):
        self.put(self._id, {'notes': notes})
        self._notes = notes

    @property
    def tasks(self):
        json_resp = self.get("/".join([self._id, 'tasks']))
        import pdb
        pdb.set_trace()        

u = User()
User.users()
u.users()
# ws = u.workspaces()
# import pdb
# pdb.set_trace()
# # u.all_users()
# w = Workspace(151953184165)
# w.name = 'EECS'

# t = Tag(workspace_id=151953184165, name='yolo')
import pdb
pdb.set_trace()
