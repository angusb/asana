"""
An API wrapper for the Asana API. 

Official documentation can be found here: http://developer.asana.com/documentation/
"""

import ConfigParser
import requests
import datetime
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
            raise AsanaError('Error: HTTP Status %s: %s' %
                            (r.status_code, error_message))
        elif sc == 500:
            phrase = json.loads(r.text)['errors'][0]['phrase']
            raise AsanaError('HTTP Status %s: %s (phrase: %s)' %
                            (r.status_code, error_message, ph))

    def _handle_response(self, r):
        """Check the headers. If there is an error raise an AsanaError,
        otherwise return the data.

        Args:
            r (request obj): request object to check headers of

        Returns:
            dict: json response from Asana
        """
        if r.headers['content-type'].split(';')[0] == 'application/json':
            return json.loads(r.text)['data']
        else:
            raise AsanaError('Did not receive json from api: %s' % str(r))

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
                 parent_id=None,
                 **kwargs):
        super(Task, self).__init__()

        if (task_id and workspace_id) or \
           (workspace_id and task_id) or \
           (task_id and parent_id):
            raise AsanaError('A Task must be created with exactly one of task_id, workspace_id, or parent_id') #TODO: pep8
        elif task_id and kwargs:
            raise AsanaError('Bad arguments')

        if task_id:
            jr = self.get(task_id)
        elif workspace_id:
            merged_post_params = dict([('workspace', workspace_id)] +
                                      kwargs.items()) # TODO: what about bad kwargs?
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
        self._workspace = None

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
    def parent(self):
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
        return [Tag(elt['id']) for elt in jr]

    @property
    def subtasks(self):
        jr = self.get('%s/subtasks' % self._id)
        return [Task(elt['id']) for elt in jr]

    @property
    def comments(self):
        jr = self.get('%s/stories' % self._id)
        return [Story(elt['id']) for elt in jr]

    @assignee.setter
    def assignee(self, user):
        try:
            user_id = user.id
        except AttributeError:
            raise AsanaError("Requires a User object.", user)

        self.put(self._id, {'assignee': user_id})
        self.assignee = user

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
        return filter(lambda x: True if x.id == tag_id else False, arr)

    def remove_tag(self, tag):
        if isinstance(tag, int) or isinstance(tag, str):
            self.post('%d/removeTag' % tag, {'tag': tag})
            self._tags = _remove_tag_helper(int(tag), self._tags)
        elif isinstance(tag, Tag):
            self.post('%d/removeTag' % tag.id, {'tag': tag.id})
            self._tags = _remove_tag_helper(tag.id, self._tags)
        else:
            raise AsanaError("Requires a int, str, or Tag object")

    # TODO: results in 2 API calls. Constraining to 1 would require verbose Story constructor?
    def add_comment(self, text):
        jr = self.post('%s/stories' % self._id)
        return Story(jr['id'])

    def add_subtask(self, **kwargs):
        return Task(parent_id=self._id, kwargs=kwargs)

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

    @property
    def users(self):
        jr = self.get('%s/users' % self._id)
        return [User(elt['id']) for elt in jr]

    @property
    def projects(self):
        jr = self.get('%s/projects' % self._id)
        return [Project(elt['id']) for elt in jr]

    @property
    def tags(self):
        jr = self.get('%s/tags' % self._id)
        return [Tag(elt['id']) for elt in jr]

    @property
    def tasks(self):
        jr = self.get('%s/tasks' % self._id)
        return [Task(elt['id']) for elt in jr]

    @name.setter
    def name(self, name):
        self.put(self._id, {'name': name})
        self._name = name

    def create_project(self, name=None, notes=None, archived=False):
        return Project(workspace_id=self._id,
                       name=name,
                       notes=notes,
                       archived=archived)

    def create_tag(self, name=None, notes=None):
        return Tag(workspace_id=self._id,
                   name=name,
                   notes=notes)

    def create_task(self, **kwargs):
        return Task(workspace_id=self._id,
                    kwargs=kwargs)

    def find_user(self, name=None, email=None, return_first_match=True):
        if name and email or (not email and not name):
            raise AsanaError('find_user requires a name or email, not both.')

        users = self.users
        if name:
            users = filter(lambda x: x.name == name, users)
            if return_first_match and users:
                return users[0]

            return users

        users = filter(lambda x: x.email == email, users)
        return users[0] if users else []

    def find_projects(self, archived=False): # TODO redundant to searching self.projects?
        """Returns a list of projects with an archive status of archived.

        Kwargs:
            archived (bool): defaulted to False.
        """
        jr = self.get('%s/projects' % self._id, {'archived': archived})
        return [Project(elt['id']) for elt in jr]

    def find_tasks(self, user):
        """Returns a list of tasks assigned to user within this workspace.

        Args:
            user (User): assignee
        """
        try:
            user_id = user.id
        except AttributeError:
            raise AsanaError("Requires a User object.", user)

        jr = self.get('%s/tasks' % self._id, {'assignee': user.id})
        return [User(elt['id']) for elt in jr]


class Tag(AsanaResource):
    def __init__(self,
                 tag_id=None,
                 workspace_id=None,
                 name=None,
                 notes=None):
        super(Tag, self).__init__()

        if (workspace_id and tag_id) or (tag_id and (name or notes)):
            raise AsanaError('Bad Arguments.')
        elif tag_id:
            jr = self.get(tag_id)
        elif workspace_id:
            payload = {'workspace': workspace_id}
            if name:
                payload['name'] = name
            if notes:
                payload['notes'] = notes
            jr = self.post(data=payload)

        self._id = jr['id']
        self._name = jr['name']
        self._notes = jr['notes']
        self._created_at = self._utcstr_to_datetime(jr['created_at'])
        self._workspace = None

    # Concisely define trivial getters
    id = property(lambda self: self._id)
    name = property(lambda self: self._name)
    notes = property(lambda self: self._notes)
    created_at = property(lambda self: self._created_at)

    @property
    def resource(self):
        return 'tags'

    @property
    def workspace(self):
        if not self._workspace:
            jr = self.get(self._id)
            self._workspace = Workspace(jr['workspace']['id'])
        return self._workspace

    @property
    def followers(self):
        """Return a list of all Users following this Tag"""
        jr = self.get(self._id)
        return [User(elt['id']) for elt in jr['followers']]

    @property
    def tasks(self):
        """Return a list of all Tasks objects associated with this tag"""
        jr = self.get('%s/tasks' % self._id)
        return [Tag(elt['id'] for elt in jr['tasks'])]

    @name.setter
    def name(self, name):
        self.put(self._id, {'name': name})
        self._name = name

    @notes.setter
    def notes(self, notes):
        self.put(self._id, {'notes': notes})
        self._notes = notes

class Project(AsanaResource):
    def __init__(self,
                 project_id=None,
                 workspace_id=None,
                 name=None,
                 notes=None,
                 archived=None): # Should archived be in the constructor? technically, but practically?
        super(Project, self).__init__()

        if project_id and workspace_id:
            raise AsanaError('Bad Arguments')
        elif project_id and (name or notes or archived):
            raise AsanaError('Bad Arguments')
        elif project_id:
            jr = self.get(project_id)
        elif workspace_id:
            payload = {'workspace': workspace_id}
            if name:
                payload['name'] = name
            if notes:
                payload['notes'] = notes
            if archived:
                payload['archived'] = archived

            jr = self.post(data=payload)

        self._id = jr['id']
        self._name = jr['name']
        self._notes = jr['notes']
        self._archived = jr['archived']
        self._created_at = self._utcstr_to_datetime(jr['created_at'])
        self._modified_at = self._utcstr_to_datetime(jr['modified_at'])
        self._workspace = None

    id = property(lambda self: self._id)
    name = property(lambda self: self._name)
    notes = property(lambda self: self._notes)
    archived = property(lambda self: self._archived)
    created_at = property(lambda self: self._created_at)
    modified_at = property(lambda self: self._modified_at)

    @property
    def resource(self):
        return 'projects'

    @property
    def workspace(self):
        """Workspace can never be changed, nor should we expect
        it to change. Compute on the fly and cache for further calls"""
        if not self._workspace:
            jr = self.get(self._id)
            self._workspace = Workspace(jr['workspace']['id'])
        return self._workspace

    @property
    def tasks(self):
        jr = self.get('%s/tasks' % self._id)
        return [Task(elt['id']) for elt in jr]

    @property
    def followers(self):
        jr = self.get(self._id)
        return [User(elt['id']) for elt in jr['followers']]

    @property
    def comments(self):
        jr = self.get('%s/stories' % self._id)
        return [Story(elt['id']) for elt in jr]

    @archived.setter
    def archived(self, archived):
        self.put(self._id, {'archived': archived})
        self._archived = archived

    @name.setter
    def name(self, name):
        self.put(self._id, {'name': name})
        self._name = name

    @notes.setter
    def notes(self, notes):
        self.put(self._id, {'notes': notes})
        self._notes = notes
        print self.tasks

    # TODO: results in 2 API calls. Constraining to 1 would require verbose Story constructor?
    #       or should this be a void method?
    def add_comment(self, text):
        jr = self.post('%s/stories' % self._id)
        return Story(jr['id'])

class Story(AsanaResource):
    def __init__(self, story_id):
        super(Story, self).__init__()
        jr = self.get(story_id)
        self._id = jr['id']
        self._text = jr['text']
        self._source = jr['source']
        self._story_type = jr['type']
        self._created_at = self._utcstr_to_datetime(jr['created_at'])

    id = property(lambda self: self._id)
    text = property(lambda self: self._text)
    source = property(lambda self: self._source)
    story_type = property(lambda self: self._story_type)
    created_at = property(lambda self: self._created_at)

    @property
    def resource(self):
        return 'stories'

    @property
    def created_by(self):
        jr = self.get(self._id)
        return User(jr['created_by']['id'])

    # TODO: what's a good interface for the caller? Ideally, he doesn't want to have to test types...
    @property
    def target(self):
        """Returns the object that this story is associated with. May be a
        task or project.
        """
        pass # TODO

#u = User()
#User.users()
#u.users()
# ws = u.workspaces()
# import pdb
# pdb.set_trace()
# # u.all_users()
# w = Workspace(151953184165)
# w.name = 'EECS'

# import pdb
# pdb.set_trace()
# task = Task(workspace_id=151953184165)
# print task.id

# t = Tag(workspace_id=151953184165, name='yolo')
# print t.id
# print t.followers
# print t.notes
# t.notes = "lolol"
# print t.notes

