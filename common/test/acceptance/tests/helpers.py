"""
Test helper functions and base classes.
"""
import unittest
import functools
import requests
from path import path
from bok_choy.web_app_test import WebAppTest

from ..pages.studio.auto_auth import AutoAuthPage
from ..fixtures.course import CourseFixture


def skip_if_browser(browser):
    """
    Method decorator that skips a test if browser is `browser`

    Args:
        browser (str): name of internet browser

    Returns:
        Decorated function

    """
    def decorator(test_function):
        @functools.wraps(test_function)
        def wrapper(self, *args, **kwargs):
            if self.browser.name == browser:
                raise unittest.SkipTest('Skipping as this test will not work with {}'.format(browser))
            test_function(self, *args, **kwargs)
        return wrapper
    return decorator


def is_youtube_available():
    """
    Check if the required youtube urls are available.

    If a URL in `youtube_api_urls` is not reachable then subsequent URLs will not be checked.

    Returns:
        bool:

    """

    youtube_api_urls = {
        'main': 'https://www.youtube.com/',
        'player': 'http://www.youtube.com/iframe_api',
        'metadata': 'http://gdata.youtube.com/feeds/api/videos/',
        # For transcripts, you need to check an actual video, so we will
        # just specify our default video and see if that one is available.
        'transcript': 'http://video.google.com/timedtext?lang=en&v=OEoXaMPEzfM',
    }

    for url in youtube_api_urls.itervalues():
        try:
            response = requests.get(url, allow_redirects=False)
        except requests.exceptions.ConnectionError:
            return False

        if response.status_code >= 300:
            return False

    return True


def load_data_str(rel_path):
    """
    Load a file from the "data" directory as a string.
    `rel_path` is the path relative to the data directory.
    """
    full_path = path(__file__).abspath().dirname() / "data" / rel_path  # pylint: disable=E1120
    with open(full_path) as data_file:
        return data_file.read()


class UniqueCourseTest(WebAppTest):
    """
    Test that provides a unique course ID.
    """

    COURSE_ID_SEPARATOR = "/"

    def __init__(self, *args, **kwargs):
        """
        Create a unique course ID.
        """
        super(UniqueCourseTest, self).__init__(*args, **kwargs)

    def setUp(self):
        super(UniqueCourseTest, self).setUp()

        self.course_info = {
            'org': 'test_org',
            'number': self.unique_id,
            'run': 'test_run',
            'display_name': 'Test Course' + self.unique_id
        }

    @property
    def course_id(self):
        return self.COURSE_ID_SEPARATOR.join([
            self.course_info['org'],
            self.course_info['number'],
            self.course_info['run']
        ])


class StudioCourseTest(UniqueCourseTest):
    """
    Base class for all Studio course tests.
    """

    def setUp(self):
        """
        Install a course with no content using a fixture.
        """
        super(StudioCourseTest, self).setUp()

        self.course_fixture = CourseFixture(
            self.course_info['org'],
            self.course_info['number'],
            self.course_info['run'],
            self.course_info['display_name']
        )
        self.populate_course_fixture(self.course_fixture)
        self.course_fixture.install()
        self.user = self.course_fixture.user
        self.log_in(self.user)

    def populate_course_fixture(self, course_fixture):
        """
        Populate the children of the test course fixture.
        """
        pass

    def log_in(self, user, is_staff=False):
        """
        Log in as the user that created the course. The user will be given instructor access
        to the course and enrolled in it. By default the user will not have staff access unless
        is_staff is passed as True.
        """
        self.auth_page = AutoAuthPage(
            self.browser,
            staff=is_staff,
            username=user.get('username'),
            email=user.get('email'),
            password=user.get('password')
        )
        self.auth_page.visit()
