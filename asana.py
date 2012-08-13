#!/usr/bin/env python

import requests
import optparse
import getpass
import time

try:
    import simplejson as json
except ImportError:
    import json
from pprint import pprint


class AsanaAPI(object):
    def __init__(self, apikey, debug=False):
        self.debug = debug
        self.asana_url = "https://app.asana.com/api"
        self.api_version = "1.0"
        self.aurl = "/".join([self.asana_url, self.api_version])
        self.apikey = apikey
        self.bauth = self._get_basic_auth()

    def _get_basic_auth(self):
        """Get basic auth creds
        :returns: the basic auth string
        """
        s = self.apikey + ":"
        return s.encode("base64").rstrip()

    def _check_http_status(self, r):
        """Check the status code. Raise an exception if there's an error with
        the status code and message."""
        sc = r.status_code
        if sc == 200 or sc == 201:
            return

        error_message = json.loads(r.text)['errors'][0]['message']
        if sc in [400, 401, 403, 404]:
            raise Exception('Error: HTTP Status %s: %s' % (r.status_code, error_message))
        elif sc == 500:
            phrase = json.loads(r.text)['errors'][0]['phrase'] # 500 errors only
            raise Exception('HTTP Status %s: %s (phrase: %s)' % \
                (r.status_code, error_message, ph))

    def _handle_response(self, r):
        """Check the headers. If there is an error raise an Exception,
        otherwise return the data."""
        if r.headers['content-type'].split(';')[0] == 'application/json':
            return json.loads(r.text)['data']
        else:
            raise Exception('Did not receive json from api: %s' % str(r))

    def _asana(self, api_target):
        """Submits a get to the Asana API and returns the result."""
        target = "/".join([self.aurl, api_target])
        if self.debug:
            print "-> Calling: %s" % target

        r = requests.get(target, auth=(self.apikey, ""))
        self._check_http_status(r)
        return self._handle_response(r)

    def _asana_post(self, api_target, data):
        """Submits a post to the Asana API and returns the result."""
        target = "/".join([self.aurl, api_target])
        if self.debug:
            print "-> Posting to: %s" % target
            print "-> Post payload:"
            pprint(data)

        r = requests.post(target, auth=(self.apikey, ""), data=data)
        self._check_http_status(r)
        return self._handle_response(r)

    def _asana_put(self, api_target, data):
        """Submits a put to the Asana API and returns the result."""
        target = "/".join([self.aurl, api_target])

        r = requests.put(target, auth=(self.apikey, ""), data=data)
        self._check_http_status(r)
        return self._handle_response(r)


    #---- Users ----#
    def user_info(self, user_id="me"):
        return self._asana('users/%s' % user_id)

    def list_users(self, workspace_id=None, filters=[]):
        if workspace_id:
            return self._asana('workspaces/%s/users' % workspace_id)

        if filters:
            fkeys = [x.strip().lower() for x in filters]
            fields = ",".join(fkeys)
            return self._asana('users?opt_fields=%s' % fields)
        else:
            return self._asana('users')


    #---- Projects ----#
    def list_projects(self, workspace_id=None, archived=None):
        target = 'projects'

        if workspace_id:
            target += '?workspace=%d' % workspace_id

        if archived:
            target += '?archived=%s' % archived

        return self._asana(target)

    def get_project(self, project_id):
        return self._asana('projects/%d' % project_id)

    def get_project_tasks(self, project_id):
        return self._asana('projects/%d/tasks' % project_id)

    def add_project_task(self, task_id, project_id):
        return self._asana_post('tasks/%d/addProject' % task_id, {'project': project_id})

    def rm_project_task(self, task_id, project_id):
        return self._asana_post('tasks/%d/removeProject' % task_id, {'project': project_id})

    def update_project(self):
        #TODO: All the things!
        return None

    def create_project(self, name, notes, workspace, archived=False):
        payload = {'name': name, 'notes': notes, 'workspace': workspace}
        if archived:
            payload['archived': 'true']
        return self._asana_post('projects', payload)

    def add_project_to_task(self, project_id, task_id):
        payload = {'project': project_id}
        return self._asana_post('tasks/%s/addProject' % task_id, payload)


    #---- Stories ----#
    def list_stories(self, task_id=None, project_id=None):
        if not task_id and not project_id:
            raise Exception("Must provide a task_id or project_id")

        if task_id:
            return self._asana('tasks/%d/stories' % task_id)
        else:
            return self._asana('projects/%d/stories' % project_id)

    def get_story(self, story_id):
        return self._asana('stories/%d' % story_id)

    def add_story(self, text, task_id=None, project_id=None):
        if not task_id and not project_id:
            raise Exception("Must provide a task_id or project_id")

        if task_id:
            return self._asana_post('tasks/%d/stories' % task_id, {'text': text})
        else:
            return self._asana_post('projects/%d/stories' % project_id, {'text': text})


    #---- Workspaces ----#
    def list_workspaces(self):
        return self._asana('workspaces')

    def update_workspace(self, workspace_id, name=None):
        if name:
            return self_asana_put('workspaces/%d' % workspace_id, {'name': name})


    #---- Tasks ----#
    def create_task(self, name, workspace_id, assignee_id=None, assignee_status=None,
                    completed=False, due_on=None, followers=None, notes=None):
        payload = self._set_task_payload(name=name, assignee_id=assignee_id or 'me', due_on=due_on,
                                         assignee_status=assignee_status, notes=notes, 
                                         completed=completed, followers=followers)
        payload['workspace'] = workspace_id

        return self._asana_post('tasks', payload)

    def update_task(self, task_id, name=None, assignee_id=None, assignee_status=None,
                    completed=None, due_on=None, followers=None, notes=None):
        payload = self._set_task_payload(name=name, assignee_id=assignee_id, due_on=due_on,
                                         assignee_status=assignee_status, notes=notes, 
                                         completed=completed, followers=followers)

        return self._asana_put('tasks/%d' % task_id, payload)

    def list_tasks(self, project_id=None, workspace_id=None, assignee_id='me'):
        if not project_id and not workspace_id:
            raise Exception("Must provide a project_id or workspace_id")

        if project_id:
            target = 'tasks?project=%d' % project_id
        else:
            target = 'tasks?workspace=%d&assignee=%s' % (workspace, assignee_id)

        return self._asana(target)

    def get_task(self, task_id):
        return self._asana("tasks/%d" % task_id)

    def add_tag_task(self, task_id, tag_id):
        return self._asana_post('tasks/%d/addTag' % task_id, {'tag': tag_id})

    def rm_tag_task(self, task_id, tag_id):
        return self._asana_post('tasks/%d/removeTag' % task_id, {'tag': tag_id})

    def _set_task_payload(self, name=None, assignee_id=None, assignee_status=None, 
                          completed=False, due_on=None, followers=None, notes=None):
        payload = {}
        if name:
            payload['name'] = name

        if assignee_id:
            payload['assignee'] = assignee_id

        if assignee_status in ['inbox', 'later', 'today', 'upcoming']:
            payload['assignee_status'] = assignee_status
        elif assignee_status:
            raise Exception('Bad task assignee status')

        if completed is not None:
            payload['completed'] = completed

        if due_on:
            try:
                vd = time.strptime(due_on, '%Y-%m-%d')
            except ValueError:
                raise Exception('Bad task due date: %s' % due_on)

        if followers:
            for pos, person in enumerate(followers):
                payload['followers[%d]' % pos] = person

        if notes:
            payload['notes'] = notes

        return payload


    #---- Tags ----#
    def get_tags(self, workspace_id):
        return self._asana('workspaces/%d/tags' % workspace_id)

    def get_tag_tasks(self, tag_id):
        return self._asana('tags/%d/tasks' % tag_id)        

    def add_tag(self, name, workspace_id):
        return self._asana_post('tags?workspace=%d&name=%s' % (workspace_id, name))

    def update_tag(self, tag_id, name=None, notes=None):
        payload = {}
        if name:
            payload['name'] = name

        if notes:
            payload['notes'] = notes

        if notes or name:
            return self._asana_put('tags/%d' % tag_id, payload)
