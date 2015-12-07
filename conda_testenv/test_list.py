import conda
import conda.cli.main_list
import conda.install as install
import conda_build.build
import conda_build.metadata
from conda_build.utils import rm_rf
from conda_build.create_test import (create_files, create_shell_files,
                                     create_py_files, create_pl_files)
from conda_build.config import config
import os
import subprocess

from os.path import exists, isdir, isfile, islink, join



def list_packages(prefix):
    """ List sources of packages in an environment """
    installed = install.linked(prefix)
    return_this = None
    for dist in conda.cli.main_list.get_packages(installed, None):
        info = install.is_linked(prefix, dist)
        print(info['link']['source'])
        recipe_exist(info['link']['source'])
    return return_this

def recipe_exist(source):
    """ Find the recipe in a source. """
    meta_dir = join(source, 'info', 'recipe')
    if not isdir(meta_dir):
        return set()
    return set(fn[:-5] for fn in os.listdir(meta_dir) if fn.endswith('.json'))

def get_metadata(recipe_path):
    """return recipe as a metadata object"""
    return conda_build.metadata.MetaData(recipe_path)

def test(m, verbose=True, channel_urls=(), override_channels=False):
    '''
    Execute any test scripts for the given package.

    :param m: Package's metadata.
    :type m: Metadata
    '''
    # remove from package cache
    conda_build.build.rm_pkgs_cache(m.dist())

    print('\t0. config.croot', config.croot)
    tmp_dir = join(config.croot, 'test-tmp_dir')
    print('\t1. tmp_dir', tmp_dir)
    rm_rf(tmp_dir)
    os.makedirs(tmp_dir)
    create_files(tmp_dir, m)
    # Make Perl or Python-specific test files
    if m.name().startswith('perl-'):
        pl_files = create_pl_files(tmp_dir, m) 
        py_files = False
    else:
        py_files = create_py_files(tmp_dir, m)
        pl_files = False
    shell_files = create_shell_files(tmp_dir, m)
    if not (py_files or shell_files or pl_files):
        print("Nothing to test for:", m.dist())
        return

    print("TEST START:", m.dist())
    env = dict(os.environ)
    if py_files:
        try:
            subprocess.check_call([config.test_python, '-s',
                                   join(tmp_dir, 'run_test.py')],
                                  env=env, cwd=tmp_dir)
        except subprocess.CalledProcessError:
            conda_build.build.tests_failed(m)
    if pl_files:
        try:
            subprocess.check_call([config.test_perl,
                                   join(tmp_dir, 'run_test.pl')],
                                  env=env, cwd=tmp_dir)
        except subprocess.CalledProcessError:
            conda_build.build.tests_failed(m)
    if shell_files:
        if sys.platform == 'win32':
            test_file = join(tmp_dir, 'run_test.bat')
            cmd = [os.environ['COMSPEC'], '/c', 'call', test_file]
            try:
                subprocess.check_call(cmd, env=env, cwd=tmp_dir)
            except subprocess.CalledProcessError:
                conda_build.build.tests_failed(m)
        else:
            test_file = join(tmp_dir, 'run_test.sh')
            # TODO: Run the test/commands here instead of in run_test.py
            cmd = ['/bin/bash', '-x', '-e', test_file]
            try:
                subprocess.check_call(cmd, env=env, cwd=tmp_dir)
            except subprocess.CalledProcessError:
                conda_build.build.tests_failed(m)
    print("TEST END:", m.dist())

def run_tests(env_prefix):
    list_packages(env_prefix)
