"""
Internationalization tasks

NOTE: if a function has **kwargs, it means it is a pretask
for a task taking certain args/options (i.e. **kwargs are ignored)
"""
from __future__ import print_function

import os
import sys
from distutils.spawn import find_executable

from path import path
from invoke import task, Collection
from invoke import run as sh
try:
    from pygments.console import colorize
except ImportError:
    colorize = lambda color, text: text
from .utils.cmd import cmd
from .utils.envs import Env
from .test import test_i18n

I18N_REPORT_DIR = Env.REPORT_DIR / 'i18n'
I18N_XUNIT_REPORT = I18N_REPORT_DIR.joinpath('nosetests.xml')

ns = Collection()
ns_validate = Collection('validate')
ns_robot = Collection('robot')


@task('i18n.validate.gettext', 'assets.update')
def extract(verbose=False, **kwargs):
    """
    Extract localizable strings from sources
    Params:
        verbose=False Display verbose output
    """
    executable = Env.REPO_ROOT / 'i18n/extract.py'
    print("Executable", executable)
    if verbose:
        sh(cmd(executable, '-vv'))
    else:
        sh(cmd(executable))

ns.add_task(extract)


@task('i18n.extract')
def generate(strict=False):
    """
    Compile localizable strings from sources, extracting strings first.
    Params:
        strict=False Complain if files are missing
    """
    executable = Env.REPO_ROOT / 'i18n/generate.py'
    if strict:
        sh(cmd(executable, '--strict'))
    else:
        sh(cmd(executable))

ns.add_task(generate, default=True)


@task('i18n.extract')
def dummy():
    """
    Simulate international translation by generating dummy strings
    corresponding to source strings.
    """
    executable = Env.REPO_ROOT / 'i18n/dummy.py'
    sh(cmd(executable))

ns.add_task(dummy)


@task
def validate_gettext(**kwargs):
    """Make sure GNU gettext utilities are available"""
    if find_executable('xgettext') is None:
        err = (
            "Cannot locate GNU gettext utilities, which are required by Django "
            "for internationalization.\n See "
            "https://docs.djangoproject.com/en/dev/topics/i18n/translation/#message-files\n"
            "Try downloading them from http://www.gnu.org/software/gettext/"
        )
        print(colorize("darkred", err))
        sys.exit(1)

ns_validate.add_task(validate_gettext, 'gettext')

@task
def validate_transifex_config():
    """Make sure config file with username/password exists"""
    pathstr = os.environ['HOME'] + '/.transifexrc'
    config_file = path(pathstr)
    if not (config_file.exists() and config_file.size > 0):
        print(colorize("darkred",
                       "Cannot connect to Transifex, config file is missing or empty: "
                       "{}\n See http://help.transifex.com/features/client/#transifexrc"
                       .format(pathstr)))
        sys.exit(1)

ns_validate.add_task(validate_transifex_config, 'transifex')

@task
def validate_all():
    validate_gettext()
    validate_transifex_config()

ns_validate.add_task(validate_all, "all", default=True)

@task('i18n.validate.transifex')
def transifex_push():
    """Push source strings to Transifex for translation"""
    transifex_executable = Env.REPO_ROOT / 'i18n/transifex.py'
    sh(cmd(transifex_executable, 'push'))

ns.add_task(transifex_push, "push")


@task('i18n.validate.transifex')
def transifex_pull():
    """Pull translated strings from Transifex"""
    transifex_executable = Env.REPO_ROOT / 'i18n/transifex.py'
    sh(cmd(transifex_executable, 'pull'))

ns.add_task(transifex_pull, "pull")


@task("i18n.pull", "i18n.extract", "i18n.dummy")
def robot_pull():
    """Pull source strings, generato po and mo files, and validate"""
    #XXX: The develop branch of invoke allows for specifying call
    #signatures of pre tasks using the `Call` class
    sh(cmd("inv", "i18n.generate", "--strict"))
    sh(cmd("git", "clean", "-fdX", "conf/locale"))
    sh(cmd("inv", "i18n.test"))
    sh(cmd("git", "add", "conf/locale"))
    sh(cmd("git", "commit", '--message="Update translations (autogenerated message)"','--edit'))

ns_robot.add_task(robot_pull, "pull", default=True)

@task("i18n.extract", "i18n.push")
def robot_push():
    """Extract new strings, and push to transifex"""
    pass

ns_robot.add_task(robot_push, "push")

@task
def test():
    # proxy to `test.i18n`
    test_i18n()

ns.add_task(test)

ns.add_collection(ns_validate)
ns.add_collection(ns_robot)