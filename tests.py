import unittest
from AsanaResource import Tag, User, Workspace, Project

WORKSPACE_ID = 151953184165

class TestAsanaTag(unittest.TestCase):

    def setUp(self):
        self.tag = Tag(workspace_id=WORKSPACE_ID, name="tester")

    def test_name(self):
        assert self.tag.name == "tester"

    def test_notes(self):
        assert self.tag.notes == ""

        self.tag.notes = "test string"
        assert self.tag.notes == "test string"

    def test_followers(self):
        assert self.tag.followers[0].id == User().id

class TestAsanaWorkspace(unittest.TestCase):

    def setUp(self):
        w = Workspace(WORKSPACE_ID)
        self.workspace = w
        self.w_name = w.name

    def test_name(self):
        self.workspace.name = "Tomato"
        assert self.workspace.name == "Tomato"

    def tearDown(self):
        self.workspace.name = self.w_name

class TestAsanaProject(unittest.TestCase):

    def setUp(self):
        self.project_id = 151972446508 # Getting Started default project
        self.project = Project(self.project_id)

    def test_followers(self):
        assert self.project.followers[0].id == User().id

    def test_archived(self):
        assert self.project.archived == False
        self.project.archived = True
        assert self.project.archived
        self.project.archived = False


# class TestAsanaTask(unittest.TestCase):
#     def setUp(self):


if __name__ == '__main__':
    unittest.main()
