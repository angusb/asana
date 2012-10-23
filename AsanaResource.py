"""
An API wrapper for the Asana API.

Official documentation: http://developer.asana.com/documentation/
"""

import ConfigParser
import requests
import datetime

from pprint import pprint


class AsanaError(Exception):
    """Class used for throwing Asana related errors"""
    pass


class AsanaClient(object):
    def __init__(self, api_key, debug=False):
        self.asana_url = "https://app.asana.com/api"
        self.api_version = "1.0"
        self.aurl = "/".join([self.asana_url, self.api_version])
        self.api_key = api_key
        self.debug = debug

    def _utcstr_to_datetime(self, timestamp):
        """Convert a UTC formatted string to a datetime object.

        Args:
            timestamp (str): UTC formatted str (e.g '2012-02-22T02:06:58.147Z')
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

        error_message = r.json['errors'][0]['message']
        if sc in [400, 401, 403, 404, 429]:
            raise AsanaError('Error: HTTP Status %s: %s' %
                            (r.status_code, error_message))
        elif sc == 500:
            phrase = r.json['errors'][0]['phrase']
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
            return r.json['data'] # json.loads(r.text)['data']
        else:
            raise AsanaError('Did not receive json from api: %s' % str(r))

    def get(self, resource, endpoint=""):
        """Submits a get to the Asana API for a particular resource and
        returns the result. Uses the endpoint to further specify the
        resource if provided.

        Args:
            resource (str)

        Kwargs:
            endpoint (str)

        Returns:
            dict: json response from Asana
        """
        target = '/'.join([self.aurl, str(resource)])
        if endpoint:
            target = '/'.join([target, str(endpoint)])

        if self.debug:
            print "-> Calling: %s" % target

        r = requests.get(target, auth=(self.api_key, ""))
        self._check_http_status(r)
        return self._handle_response(r)

    def post(self, resource, endpoint="", data={}):
        """Submits a post to the Asana API for a given resource and
        returns the result. Uses the endpoint to further specify the
        resource if provided.

        Args:
            resource (str)

        Kwargs:
            endpoint (str)
            data (dict): post data

        Returns:
            dict: json response from Asana
        """
        target = '/'.join([self.aurl, str(resource)])
        if endpoint:
            target = '/'.join([target, str(endpoint)])

        if self.debug:
            print "-> Posting to: %s" % target
            print "-> Post payload:"
            pprint(data)

        r = requests.post(target, auth=(self.api_key, ""), data=data)
        self._check_http_status(r)
        return self._handle_response(r)

    def put(self, resource, endpoint="", data={}):
        """Submits a put to the Asana API for a given resource and
        returns the result. Uses the endpoint to further specify the
        resource if provided.

        Args:
            resource (str):

        Kwargs:
            api_target (str)
            data (dict): put data

        Returns:
            dict: json response from Asana
        """
        target = '/'.join([self.aurl, str(resource)])
        if endpoint:
            target = '/'.join([target, str(endpoint)])

        if self.debug:
            print "-> Putting to: %s" % target
            print "-> Put payload:"
            pprint(data)

        r = requests.put(target, auth=(self.api_key, ""), data=data)
        self._check_http_status(r)
        return self._handle_response(r)


class Asana(AsanaClient):
    def __init__(self, api_key=None, config_file='./asana.cfg', debug=False):
        """Creates an Asana object which is the interface to all API actions.
        A API key or a configuration file are required (not both) are required
        for intialization.

        Note: you can pass in a relative path for config_file (but no ~)

        Kwargs:
            api_key (str): used in HTTP basic auth (as username)
            confi_file (str): path to configuration file location
        """
        if api_key:
            super(Asana, self).__init__(api_key, debug)
            return

        import os
        abs_path = os.path.abspath(config_file)

        try:
            with open(abs_path) as f: pass
        except IOError as e:
            raise e

        config = ConfigParser.ConfigParser()
        config.read(config_file)
        config_section = 'Asana Configuration'
        api_key = config.get(config_section, 'api_key')
        debug = config.getboolean(config_section, 'debug')

        super(Asana, self).__init__(api_key, debug)

    @property
    def users(self):
        jr = self.get('users')
        return [User(self, elt['id']) for elt in jr]

    @property
    def workspaces(self):
        jr = self.get('workspaces')
        return [Workspace(self, elt['id']) for elt in jr]

    @property
    def projects(self):
        jr = self.get('projects')
        return [Project(self, elt['id']) for elt in jr]

    @property
    def tags(self):
        jr = self.get('tags')
        return [Tag(self, elt['id']) for elt in jr]

    def find_workspace(name, first_match=True):
        """Returns a workspace with the given name. If first_match
        is False, return all workspaces with name (Asana doesn't enforce
        unique workspace names).

        Kwargs:
            first_match (bool): whether to return all matches or the first one
        """
        workspaces = filter(lambda x: x.name == name, self.workspaces)
        if workspaces and first_match:
            return workspaces[0]

        return workspaces

    def find_tag(name, first_match=True):
        """Returns a tags with the given name. If first_match
        is False, return all tags with name (Asana doesn't enforce
        unique tag names).

        Kwargs:
            first_match (bool): whether to return all matches or the first one
        """
        tags = filter(lambda x: x.name == name, self.tags)
        if tags and first_match:
            return tags[0]

        return tags

    def User(self, user_id='me'):
        return User(self, user_id=user_id)

    def Workspace(self, workspace_id):
        return Workspace(self, workspace_id)

    def Project(self,
                project_id=None,
                workspace_id=None,
                name=None,
                notes=None,
                archived=None):
        return Project(self, project_id, workspace_id, name, notes, archived)

    def Tag(self,
            tag_id=None,
            workspace_id=None,
            name=None,
            notes=None):
        return Tag(self, tag_id, workspace_id, name, notes)

    def Task(self,
             task_id=None,
             workspace_id=None,
             parent_id=None,
             **kwargs):
        return Task(self, task_id, workspace_id, parent_id, **kwargs)

    def Story(self, story_id):
        return Story(self, story_id)


class AsanaResource(object):
    def _utcstr_to_datetime(self, timestamp):
        """Convert a UTC formatted string to a datetime object.

        Args:
            timestamp (str): UTC formatted str (e.g '2012-02-22T02:06:58.147Z')
        """
        timestamp = timestamp.replace('T', ' ').replace('Z', '')
        return datetime.datetime.strptime(timestamp, '%Y-%m-%d %H:%M:%S.%f')


class User(AsanaResource):
    def __init__(self, api, user_id='me'):
        print user_id
        self.api = api
        self.resrc = 'users'
        jr = self.api.get(self.resrc, user_id)
        self._name = jr['name']
        self._email = jr['email']
        self._id = jr['id']

    id = property(lambda self: self._id)
    name = property(lambda self: self._name)
    email = property(lambda self: self._email)

    @property
    def workspaces(self):
        jr = self.api.get(self.resrc, self._id)
        return [Workspace(self.api, elt['id']) for elt in jr['workspaces']]


class Task(AsanaResource):
    def __init__(self,
                 api,
                 task_id=None,
                 workspace_id=None,
                 parent_id=None,
                 **kwargs):
        self.api = api
        self.resrc = 'tasks'

        if (task_id and workspace_id) or \
           (workspace_id and task_id) or \
           (task_id and parent_id):
            raise AsanaError('A Task must be created with exactly one '
                             'of task_id, workspace_id, or parent_id')
        elif task_id and kwargs:
            raise AsanaError('Bad arguments')

        if task_id:
            jr = self.api.get(self.resrc, task_id)
        elif workspace_id:
            # TODO: what about bad kwargs?
            merged_post_params = dict([('workspace', workspace_id)] +
                                      kwargs.items())
            jr = self.api.post(self.resrc, data=merged_post_params)
        elif parent_id:
            jr = self.api.post(self.resrc, '%s/subtasks' % parent_id, kwargs)
        else:
            raise AsanaError('Bug encountered.')

        date_frmtr = lambda d: self._utcstr_to_datetime(d) if d else None

        self._id = jr['id']
        self._name = jr['name']
        self._notes = jr['notes']
        self._assignee_status = jr['assignee_status']
        self._created_at = self._utcstr_to_datetime(jr['created_at'])
        self._modified_at = self._utcstr_to_datetime(jr['modified_at'])
        self._completed_at = date_frmtr(jr['completed_at'])
        self._completed = jr['completed']
        self._due_on = jr['due_on'] # TODO
        self._tags = jr['tags']
        self._projects = jr['projects']
        self._workspace = None

    id = property(lambda self: self._id)
    name = property(lambda self: self._name)
    notes = property(lambda self: self._notes)
    created_at = property(lambda self: self._created_at)
    modified_at = property(lambda self: self._modified_at)
    completed_at = property(lambda self: self._completed_at)
    due_on = property(lambda self: self._due_on)
    completed = property(lambda self: self._completed)
    assignee_status = property(lambda self: self._assignee_status)

    @property
    def parent(self):
        jr = self.api.get(self.resrc, self._id)
        if jr['parent']:
            return User(self.api, jr['parent']['id'])
        else:
            return None

    @property
    def workspace(self):
        jr = self.api.get(self.resrc, self._id)
        return Workspace(self.api, jr['workspace']['id'])

    @property
    def assignee(self):
        jr = self.api.get(self.resrc, self._id)
        if jr['assignee']:
            return User(self.api, jr['assignee']['id'])
        else:
            return None

    @property
    def followers(self):
        jr = self.api.get(self.resrc, self._id)
        if jr['followers']:
            return [User(self.api, elt['id']) for elt in jr['followers']]
        else:
            return []

    @property
    def projects(self):
        jr = self.api.get(self.resrc, self._id)
        if jr['projects']:
            return [Project(self.api, elt['id']) for elt in jr['projects']]
        else:
            return []

    @property
    def tags(self):
        jr = self.api.get(self.resrc, '%s/tags' % self._id)
        return [Tag(self.api, elt['id']) for elt in jr]

    @property
    def subtasks(self):
        jr = self.api.get(self.resrc, '%s/subtasks' % self._id)
        return [Task(self.api, elt['id']) for elt in jr]

    @property
    def comments(self):
        jr = self.api.get(self.resrc, '%s/stories' % self._id)
        return [Story(self.api, elt['id']) for elt in jr]

    @assignee.setter
    def assignee(self, user):
        try:
            user_id = user.id
        except AttributeError:
            raise AsanaError("Requires a User object.", user)

        self.api.put(self.resrc, self._id, {'assignee': user_id})
        self.assignee = user

    @assignee_status.setter
    def assignee_status(self, status):
        ok_status = ['upcoming', 'inbox', 'later', 'today', 'upcoming']
        if status not in ok_status:
            s = ','.join(ok_status)
            raise AsanaError('Requries a status to be one of the following:' + s)

        self.api.put(self.resrc, self._id, {'status': status})
        self._assignee_status = status

    @name.setter
    def name(self, name):
        self.api.put(self.resrc, self._id, {'name': name})
        self._name = name

    @notes.setter
    def notes(self, notes):
        self.api.put(self.resrc, self._id, {'notes': notes})
        self._notes = notes

    @completed.setter
    def completed(self, completed):
        self.api.put(self.resrc, self._id, {'completed': completed})
        self._completed = completed

    def _change_obj(self, arg, endpoint, datatype):
        """Internal method that abstracts the addition or removal or addition
        of tags and projects. Throws an error if arg is not of the right type,
        otherwise makes the requested post to endpint.

        Args:
            arg (obj)
            endpoint (str) - where we will post to
            data (dict) - data we will post
            datatype (str) - used to construct post data
        """
        if isinstance(arg, int) or isinstance(arg, str):
            self.api.post(self.resrc, endpoint, {datatype: arg})
        elif datatype == 'tag' and isinstance(arg, Tag):
            self.api.post(self.resrc, endpoint, {datatype: arg.id})
        elif datatype == 'project' and isinstance(arg, Project):
            self.api.post(self.resrc, endpoint, {datatype: arg.id})
        else:
            raise AsanaError('Requires an int, str, or %s' % datatype)

    def add_project(self, project):
        """Add a project to this task. Tasks can be listed under multiple
        projects within Asana.

        Args:
            project (str, int, project) - project id to add (str, int) or
                                          Project object
        """
        self._change_obj(project, '%s/addProject' % self._id, 'project')

    def remove_project(self, project):
        """Remove a project from this task.

        Args:
            project (str, int, project) - project id to add (str, int) or
                                          Project object
        """
        self._change_obj(project, '%s/removeProject' % self._id, 'project')

    def add_tag(self, tag):
        """Add a tag to this task. A task can have multiple tags.

        Args:
            tag (str, int, Tag) - tag id to add (str, or int) or Tag object
        """
        self._change_obj(tag, '%s/addTag' % self._id, 'tag')

    def remove_tag(self, tag):
        """Remove a tag from this task.

        Args:
            tag (str, int, Tag) - tag id to remove (str, or int) or Tag object
        """
        self._change_obj(tag, '%s/removeTag' % self._id, 'tag')

    # TODO: results in 2 API calls. Constraining to 1 would require verbose
    #       Story constructor? Also, should I return a coment object?
    def add_comment(self, text):
        """Add a comment to this task.

        Args:
            text (str) - comment
        """
        jr = self.api.post(self.resrc, '%s/stories' % self._id,
                           {'text': text})
        return Story(self.api, jr['id'])

    def add_subtask(self, **kwargs):
        return Task(self.api, parent_id=self._id, kwargs=kwargs)

    def bulk_update(self, **kwargs):
        payload = {}
        pass


class Workspace(AsanaResource):
    def __init__(self, api, workspace_id):
        self.api = api
        self.resrc = 'workspaces'
        jr = self.api.get(self.resrc, workspace_id)
        self._id = jr['id']
        self._name = jr['name']

    id = property(lambda self: self._id)
    name = property(lambda self: self._name)

    @property
    def users(self):
        jr = self.api.get(self.resrc, '%s/users' % self._id)
        return [User(self.api, elt['id']) for elt in jr]

    @property
    def projects(self):
        jr = self.api.get(self.resrc, '%s/projects' % self._id)
        return [Project(self.api, elt['id']) for elt in jr]

    @property
    def tags(self):
        jr = self.api.get(self.resrc, '%s/tags' % self._id)
        return [Tag(self.api, elt['id']) for elt in jr]

    @name.setter
    def name(self, name):
        self.api.put(self.resrc, self._id, {'name': name})
        self._name = name

    def create_project(self, name=None, notes=None, archived=False):
        return Project(self.api,
                       workspace_id=self._id,
                       name=name,
                       notes=notes,
                       archived=archived)

    def create_tag(self, name=None, notes=None):
        return Tag(self.api,
                   workspace_id=self._id,
                   name=name,
                   notes=notes)

    def create_task(self, **kwargs):
        return Task(self.api, workspace_id=self._id, kwargs=kwargs)

    def find_user(self, name=None, email=None, first_match=True):
        if name and email or (not email and not name):
            raise AsanaError('find_user requires a name or email, not both.')

        users = self.users
        if name:
            users = filter(lambda x: x.name == name, users)
            if first_match and users:
                return users[0]

            return users

        users = filter(lambda x: x.email == email, users)
        return users[0] if users else []

    # TODO redundant to searching self.projects? bad implementation?
    def find_projects(self, archived=False):
        """Returns a list of projects with an archive status of archived.

        Kwargs:
            archived (bool): defaulted to False.
        """
        jr = self.api.get(self.resrc, '%s/projects' % self._id,
                          {'archived': archived})
        return [Project(self.api, elt['id']) for elt in jr]

    def find_tasks(self, user):
        """Returns a list of tasks assigned to user within this workspace.

        Args:
            user (User): assignee
        """
        try:
            user_id = user.id
        except AttributeError:
            raise AsanaError("Requires a User object.", user)

        jr = self.api.get(self.resrc,
                          '%s/tasks?assignee=%s' % (self._id, user_id))
        return [Task(self.api, elt['id']) for elt in jr]


class Tag(AsanaResource):
    def __init__(self,
                 api,
                 tag_id=None,
                 workspace_id=None,
                 name=None,
                 notes=None):

        self.api = api
        self.resrc = 'tags'

        if tag_id and workspace_id:
            raise AsanaError('Requires a tag_id or workspace_id (not both).')
        if (workspace_id and tag_id) or (tag_id and (name or notes)):
            raise AsanaError('Bad Arguments.')
        elif tag_id:
            jr = self.api.get(self.resrc, tag_id)
        elif workspace_id:
            payload = {'workspace': workspace_id}
            if name:
                payload['name'] = name
            if notes:
                payload['notes'] = notes
            jr = self.api.post(self.resrc, data=payload)

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
    def workspace(self):
        if not self._workspace:
            jr = self.api.get(self.resrc, self._id)
            self._workspace = Workspace(self.api, jr['workspace']['id'])
        return self._workspace

    @property
    def followers(self):
        """Return a list of all Users following this Tag"""
        jr = self.api.get(self.resrc, self._id)
        return [User(self.api, elt['id']) for elt in jr['followers']]

    @property
    def tasks(self):
        """Return a list of all Tasks objects associated with this tag"""
        jr = self.api.get(self.resrc, '%s/tasks' % self._id)
        return [Tag(self.api, elt['id']) for elt in jr['tasks']]

    @name.setter
    def name(self, name):
        self.api.put(self.resrc, self._id, {'name': name})
        self._name = name

    @notes.setter
    def notes(self, notes):
        self.api.put(self.resrc, self._id, {'notes': notes})
        self._notes = notes


class Project(AsanaResource):
    """Represents projects in Asana."""
    def __init__(self,
                 api,
                 project_id=None,
                 workspace_id=None,
                 name=None,
                 notes=None,
                 archived=None): # Should archived be in the constructor? technically, but practically?

        self.api = api
        self.resrc = 'projects'

        if project_id and workspace_id:
            raise AsanaError('Bad Arguments')
        elif project_id and (name or notes or archived):
            raise AsanaError('Bad Arguments')
        elif project_id:
            jr = self.api.get(self.resrc, project_id)
        elif workspace_id:
            payload = {'workspace': workspace_id}
            if name:
                payload['name'] = name
            if notes:
                payload['notes'] = notes
            if archived:
                payload['archived'] = archived

            jr = self.api.post(self.resrc, data=payload)

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
    def workspace(self):
        """Workspace can never be changed, nor should we expect
        it to change. Compute on the fly and cache for further calls"""
        if not self._workspace:
            jr = self.api.get(self.resrc, self._id)
            self._workspace = Workspace(self.api, jr['workspace']['id'])
        return self._workspace

    @property
    def tasks(self):
        jr = self.api.get(self.resrc, '%s/tasks' % self._id)
        return [Task(self.api, elt['id']) for elt in jr]

    @property
    def followers(self):
        jr = self.api.get(self.resrc, self._id)
        return [User(self.api, elt['id']) for elt in jr['followers']]

    @property
    def comments(self):
        jr = self.api.get(self.resrc, '%s/stories' % self._id)
        return [Story(self.api, elt['id']) for elt in jr]

    @archived.setter
    def archived(self, archived):
        self.api.put(self.resrc, self._id, {'archived': archived})
        self._archived = archived

    @name.setter
    def name(self, name):
        self.api.put(self.resrc, self._id, {'name': name})
        self._name = name

    @notes.setter
    def notes(self, notes):
        self.api.put(self.resrc, self._id, {'notes': notes})
        self._notes = notes

    # TODO: results in 2 API calls. Constraining to 1 would require
    #       verbose Story constructor or should this be a void method?
    def add_comment(self, text):
        jr = self.api.post(self.resrc, '%s/stories' % self._id,
                           {'text': text})
        return Story(self.api, jr['id'])


class Story(AsanaResource):
    """
    Represents stories in Asana. Currently, a comment is the only
    type of story supported by the API.
    """
    def __init__(self, api, story_id):
        self.api = api
        self.resrc = 'stories'
        jr = self.api.get(self.resrc, story_id)
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
    def created_by(self):
        jr = self.api.get(self.resrc, self._id)
        return User(self.api, jr['created_by']['id'])

    # TODO: what's a good interface for the caller?
    #       Ideally, he doesn't want to have to test types...
    @property
    def target(self):
        """Returns the object that this story is associated with. May be a
        task or project.
        """
        pass

# api = Asana('2FRy4F9.Shtc7cEjm556j2g0Jxy0Q133', debug=True)
# u = api.User(user_id=151953184167)
# print u.name
# workspace = api.workspaces[0]
# print workspace.users


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
