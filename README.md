# Asana Python API

Python wrapper for the [Asana API](http://developer.asana.com/documentation/). It's a work in progress. What we have so far:

Users:
- user_info
- list_users

Projects:
- list_projects
- get_project
- create_project
- update_project
- get_project_tasks
- add_project_task
- rm_project_task
- add_project_to_task

Stories:
- list_stories
- get_story

Workspaces
- list_workspaces
- update_workspace

Tasks:
- list_tasks
- create_task
- update_task
- add_tag_task
- rm_tag_task

Tags:
- get_tags
- get tag
- get_tag_tasks
- add_tag
- update_tag

Todo:
- Tests!
- Egg?

Sample:

    import asana
    asana_api = asana.AsanaAPI('YourAsanaAPIKey', debug=True)

    # see your workspaces
    myspaces = asana_api.list_workspaces()  #Result: [{u'id': 123456789, u'name': u'asanapy'}]

    # create a new project
    asana_api.create_project('test project', 'notes for test project', myspaces[0]['id'])

    # create a new task
    asana_api.create_task('yetanotherapitest', myspaces[0]['id'], assignee_status='later', notes='some notes')

    # add a story to task
    asana_api.add_story(mytask, 'omgwtfbbq')

