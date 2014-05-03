import os
import re
import sys
import shutil
import tempfile
import unittest

from twit import (GitExeTwitRepo, PyGit2TwitRepo, DetachedHead, _cd, _git)

PY2 = sys.version_info[0] == 2
PY3 = sys.version_info[0] == 3

class SharedTestMixin(object):
    """Mixin to test both GitRepo backends."""

    if not PY2:
        # renamed in Python 3
        def assertItemsEqual(self, *args, **kwargs):
            return self.assertCountEqual(*args, **kwargs)

    def create_temp_repo(self):
        self.workdir = tempfile.mkdtemp()
        self.old_cwd = os.getcwd()
        os.chdir(self.workdir)
        _git('init')

    def cleanup_temp_repo(self):
        os.chdir(self.old_cwd)
        shutil.rmtree(self.workdir)

    def write_file(self, name='README', content='Read me.'):
        with open(name, 'w') as wfile:
            wfile.write(content)

    def commit_file(self, name='README', content='Read me.'):
        self.write_file(name, content)
        _git('add', name)
        _git('commit', '-m', 'Created {}'.format(name))

    def assert_empty_stage(self):
        status = _git('status', '-z').rstrip('\0 ')
        if not status:
            return
        for line in status.split('\0'):
            self.assertIn(line[0], (' ', '?'))

    def assert_clean_workdir(self):
        status = _git('status', '-z').rstrip('\0 ')
        if not status:
            return
        for line in status.split('\0'):
            self.assertEqual(line[1], ' ')

    def test_current_branch(self):
        self.assertEqual('master', self.repo.current_branch)
        _git('checkout', '-b', 'newbranch')
        self.assertEqual('newbranch', self.repo.current_branch)

        self.commit_file('README')
        head_commit = _git('rev-parse', 'HEAD')
        _git('checkout', head_commit)
        with self.assertRaises(DetachedHead):
            self.repo.current_branch

    def test_refs(self):
        self.commit_file('README')
        self.assertItemsEqual(['refs/heads/master'], self.repo.refs)
        _git('branch', 'newbranch')
        self.assertItemsEqual(['refs/heads/master', 'refs/heads/newbranch'],
                self.repo.refs)
        _git('tag', 'v1.0')
        self.assertItemsEqual(['refs/heads/master', 'refs/heads/newbranch',
            'refs/tags/v1.0'], self.repo.refs)

    def test_branches(self):
        self.commit_file('README')
        self.assertItemsEqual(['master'], self.repo.branches)
        _git('branch', 'newbranch')
        self.assertItemsEqual(['master', 'newbranch'],
                self.repo.branches)
        _git('tag', 'v1.0')
        self.assertItemsEqual(['master', 'newbranch'],
                self.repo.branches)

    def test_dirty(self):
        self.write_file('README', 'original')
        self.assertTrue(self.repo.dirty)
        _git('add', 'README')
        _git('commit', '-m', 'added README')
        self.assertFalse(self.repo.dirty)
        self.write_file('README', 'changed')
        self.assertTrue(self.repo.dirty)
        _git('add', 'README')
        _git('commit', '-m', 'changed README')
        self.assertFalse(self.repo.dirty)
        self.write_file('new_file', 'new')
        self.assertTrue(self.repo.dirty)

    def test_stage_all(self):
        self.commit_file('README', 'original')
        self.commit_file('mistake', 'oops')
        self.write_file('README', 'changed')
        self.write_file('new_file', 'new')
        os.remove('mistake')
        os.mkdir('subdir')
        with _cd('subdir'):
            self.write_file('subfile')
            self.repo.stage_all()
        self.assert_clean_workdir()

    def test_unstage_all(self):
        self.write_file('file1')
        _git('add', 'file1')
        self.repo.unstage_all()
        self.assert_empty_stage()
        self.commit_file('file2')
        self.write_file('file3')
        _git('add', 'file3')
        self.repo.unstage_all()
        self.assert_empty_stage()

    def test_commit(self):
        self.write_file('file1')
        _git('add', 'file1')
        self.repo.commit('initial commit')
        self.assert_clean_workdir()
        self.write_file('file2')
        _git('add', 'file2')
        self.repo.commit('another commit')
        self.assert_clean_workdir()

    def test_save(self):
        self.write_file('file1')
        self.repo.save()
        self.assert_empty_stage()
        refs = _git('for-each-ref', '--format', '%(refname)').split('\n')
        ref_folders = [os.path.dirname(ref) for ref in refs]
        self.assertIn('refs/hidden/heads/twit/master', ref_folders)

# Use the GitRepoTestMixin to test GitExeRepo
class GitExeRepoTestCase(unittest.TestCase, SharedTestMixin):
    def setUp(self):
        self.create_temp_repo()
        self.repo = GitExeTwitRepo.from_cwd()
    def tearDown(self):
        self.cleanup_temp_repo()

# Use the GitRepoTestMixin to test PyGit2Repo
class PyGit2RepoTestCase(unittest.TestCase, SharedTestMixin):
    def setUp(self):
        self.create_temp_repo()
        self.repo = PyGit2TwitRepo.from_cwd()
    def tearDown(self):
        self.cleanup_temp_repo()
