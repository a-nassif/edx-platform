"""
Acceptance tests for Studio related to the split_test module.
"""

import json
import os
import math
from unittest import skip, skipUnless

from xmodule.partitions.partitions import Group, UserPartition
from bok_choy.promise import Promise

from ..fixtures.course import CourseFixture, XBlockFixtureDesc
from ..pages.studio.component_editor import ComponentEditorView
from ..pages.studio.settings_advanced import AdvancedSettingsPage
from ..pages.studio.settings_group_configurations import GroupConfigurationsPage
from ..pages.studio.auto_auth import AutoAuthPage
from ..pages.studio.utils import add_advanced_component
from ..pages.xblock.utils import wait_for_xblock_initialization
from .helpers import UniqueCourseTest
from test_studio_container import ContainerBase


class SplitTestMixin(object):
    """
    Mixin that contains useful methods for split_test module testing.
    """
    def verify_groups(self, container, active_groups, inactive_groups, verify_missing_groups_not_present=True):
        """
        Check that the groups appear and are correctly categorized as to active and inactive.

        Also checks that the "add missing groups" button/link is not present unless a value of False is passed
        for verify_missing_groups_not_present.
        """
        def wait_for_xblocks_to_render():
            # First xblock is the container for the page, subtract 1.
            return (len(active_groups) + len(inactive_groups) == len(container.xblocks) - 1, len(active_groups))

        Promise(wait_for_xblocks_to_render, "Number of xblocks on the page are incorrect").fulfill()

        def check_xblock_names(expected_groups, actual_blocks):
            self.assertEqual(len(expected_groups), len(actual_blocks))
            for idx, expected in enumerate(expected_groups):
                self.assertEqual('Expand or Collapse\n{}'.format(expected), actual_blocks[idx].name)

        check_xblock_names(active_groups, container.active_xblocks)
        check_xblock_names(inactive_groups, container.inactive_xblocks)

        # Verify inactive xblocks appear after active xblocks
        check_xblock_names(active_groups + inactive_groups, container.xblocks[1:])
        if verify_missing_groups_not_present:
            self.verify_add_missing_groups_button_not_present(container)

    def verify_add_missing_groups_button_not_present(self, container):
        """
        Checks that the "add missing gorups" button/link is not present.
        """
        def missing_groups_button_not_present():
            button_present = container.missing_groups_button_present()
            return (not button_present, not button_present)

        Promise(missing_groups_button_not_present, "Add missing groups button should not be showing.").fulfill()


class SplitTest(ContainerBase, SplitTestMixin):
    """
    Tests for creating and editing split test instances in Studio.
    """
    __test__ = True

    def setup_fixtures(self):
        course_fix = CourseFixture(
            self.course_info['org'],
            self.course_info['number'],
            self.course_info['run'],
            self.course_info['display_name']
        )

        course_fix.add_advanced_settings(
            {
                u"advanced_modules": {"value": ["split_test"]},
                u"user_partitions": {"value": [
                    UserPartition(0, 'Configuration alpha,beta', 'first', [Group("0", 'alpha'), Group("1", 'beta')]).to_json(),
                    UserPartition(1, 'Configuration 0,1,2', 'second', [Group("0", 'Group 0'), Group("1", 'Group 1'), Group("2", 'Group 2')]).to_json()
                ]}
            }
        )

        course_fix.add_children(
            XBlockFixtureDesc('chapter', 'Test Section').add_children(
                XBlockFixtureDesc('sequential', 'Test Subsection').add_children(
                    XBlockFixtureDesc('vertical', 'Test Unit')
                )
            )
        ).install()

        self.course_fix = course_fix

        self.user = course_fix.user

    def create_poorly_configured_split_instance(self):
        """
        Creates a split test instance with a missing group and an inactive group.

        Returns the container page.
        """
        unit = self.go_to_unit_page(make_draft=True)
        add_advanced_component(unit, 0, 'split_test')
        container = self.go_to_container_page()
        container.edit()
        component_editor = ComponentEditorView(self.browser, container.locator)
        component_editor.set_select_value_and_save('Group Configuration', 'Configuration alpha,beta')
        self.course_fix.add_advanced_settings(
            {
                u"user_partitions": {"value": [
                    UserPartition(0, 'Configuration alpha,beta', 'first',
                                  [Group("0", 'alpha'), Group("2", 'gamma')]).to_json()
                ]}
            }
        )
        self.course_fix._add_advanced_settings()
        return self.go_to_container_page()

    def test_create_and_select_group_configuration(self):
        """
        Tests creating a split test instance on the unit page, and then
        assigning the group configuration.
        """
        unit = self.go_to_unit_page(make_draft=True)
        add_advanced_component(unit, 0, 'split_test')
        container = self.go_to_container_page()
        container.edit()
        component_editor = ComponentEditorView(self.browser, container.locator)
        component_editor.set_select_value_and_save('Group Configuration', 'Configuration alpha,beta')
        self.verify_groups(container, ['alpha', 'beta'], [])

        # Switch to the other group configuration. Must navigate again to the container page so
        # that there is only a single "editor" on the page.
        container = self.go_to_container_page()
        container.edit()
        component_editor = ComponentEditorView(self.browser, container.locator)
        component_editor.set_select_value_and_save('Group Configuration', 'Configuration 0,1,2')
        self.verify_groups(container, ['Group 0', 'Group 1', 'Group 2'], ['alpha', 'beta'])

        # Reload the page to make sure the groups were persisted.
        container = self.go_to_container_page()
        self.verify_groups(container, ['Group 0', 'Group 1', 'Group 2'], ['alpha', 'beta'])

    @skip("This fails periodically where it fails to trigger the add missing groups action.Dis")
    def test_missing_group(self):
        """
        The case of a split test with invalid configuration (missing group).
        """
        container = self.create_poorly_configured_split_instance()

        # Wait for the xblock to be fully initialized so that the add button is rendered
        wait_for_xblock_initialization(self, '.xblock[data-block-type="split_test"]')

        # Click the add button and verify that the groups were added on the page
        container.add_missing_groups()
        self.verify_groups(container, ['alpha', 'gamma'], ['beta'])

        # Reload the page to make sure the groups were persisted.
        container = self.go_to_container_page()
        self.verify_groups(container, ['alpha', 'gamma'], ['beta'])

    def test_delete_inactive_group(self):
        """
        Test deleting an inactive group.
        """
        container = self.create_poorly_configured_split_instance()

        # The inactive group is the 2nd group, but it is the first one
        # with a visible delete button, so use index 0
        container.delete(0)
        self.verify_groups(container, ['alpha'], [], verify_missing_groups_not_present=False)


@skipUnless(os.environ.get('FEATURE_GROUP_CONFIGURATIONS'), 'Tests Group Configurations feature')
class SettingsMenuTest(UniqueCourseTest):
    """
    Tests that Setting menu is rendered correctly in Studio
    """

    def setUp(self):
        super(SettingsMenuTest, self).setUp()

        course_fix = CourseFixture(**self.course_info)
        course_fix.install()

        self.auth_page = AutoAuthPage(
            self.browser,
            staff=False,
            username=course_fix.user.get('username'),
            email=course_fix.user.get('email'),
            password=course_fix.user.get('password')
        )
        self.auth_page.visit()

        self.advanced_settings = AdvancedSettingsPage(
            self.browser,
            self.course_info['org'],
            self.course_info['number'],
            self.course_info['run']
        )
        self.advanced_settings.visit()

    def test_link_exist_if_split_test_enabled(self):
        """
        Ensure that the link to the "Group Configurations" page is shown in the
        Settings menu.
        """
        link_css = 'li.nav-course-settings-group-configurations a'
        self.assertFalse(self.advanced_settings.q(css=link_css).present)

        self.advanced_settings.set('Advanced Module List', '["split_test"]')

        self.browser.refresh()
        self.advanced_settings.wait_for_page()

        self.assertIn(
            "split_test",
            json.loads(self.advanced_settings.get('Advanced Module List')),
        )

        self.assertTrue(self.advanced_settings.q(css=link_css).present)

    def test_link_does_not_exist_if_split_test_disabled(self):
        """
        Ensure that the link to the "Group Configurations" page does not exist
        in the Settings menu.
        """
        link_css = 'li.nav-course-settings-group-configurations a'
        self.advanced_settings.set('Advanced Module List', '[]')
        self.browser.refresh()
        self.advanced_settings.wait_for_page()
        self.assertFalse(self.advanced_settings.q(css=link_css).present)


@skipUnless(os.environ.get('FEATURE_GROUP_CONFIGURATIONS'), 'Tests Group Configurations feature')
class GroupConfigurationsTest(ContainerBase, SplitTestMixin):
    """
    Tests that Group Configurations page works correctly with previously
    added configurations in Studio
    """
    __test__ = True

    def setup_fixtures(self):
        course_fix = CourseFixture(**self.course_info)
        course_fix.add_advanced_settings({
            u"advanced_modules": {"value": ["split_test"]},
        })
        course_fix.add_children(
            XBlockFixtureDesc('chapter', 'Test Section').add_children(
                XBlockFixtureDesc('sequential', 'Test Subsection').add_children(
                    XBlockFixtureDesc('vertical', 'Test Unit')
                )
            )
        ).install()

        self.course_fix = course_fix

        self.course_fix = course_fix
        self.user = course_fix.user

    def setUp(self):
        super(GroupConfigurationsTest, self).setUp()
        self.page = GroupConfigurationsPage(
            self.browser,
            self.course_info['org'],
            self.course_info['number'],
            self.course_info['run']
        )

    def _assert_fields(self, config, cid=None, name='', description='', groups=None):
        self.assertEqual(config.mode, 'details')

        if name:
            self.assertIn(name, config.name)

        if cid:
            self.assertEqual(cid, config.id)
        else:
            # To make sure that id is present on the page and it is not an empty.
            # We do not check the value of the id, because it's generated randomly and we cannot
            # predict this value
            self.assertTrue(config.id)

        # Expand the configuration
        config.toggle()

        if description:
            self.assertIn(description, config.description)

        if groups:
            allocation = int(math.floor(100 / len(groups)))
            self.assertEqual(groups, [group.name for group in config.groups])
            for group in config.groups:
                self.assertEqual(str(allocation) + "%", group.allocation)

        # Collapse the configuration
        config.toggle()

    def test_no_group_configurations_added(self):
        """
        Scenario: Ensure that message telling me to create a new group configuration is
        shown when group configurations were not added.
        Given I have a course without group configurations
        When I go to the Group Configuration page in Studio
        Then I see "You haven't created any group configurations yet." message
        And "Create new Group Configuration" button is available
        """
        self.page.visit()
        css = ".wrapper-content .no-group-configurations-content"
        self.assertTrue(self.page.q(css=css).present)
        self.assertIn(
            "You haven't created any group configurations yet.",
            self.page.q(css=css).text[0]
        )

    def test_group_configurations_have_correct_data(self):
        """
        Scenario: Ensure that the group configuration is rendered correctly in expanded/collapsed mode.
        Given I have a course with 2 group configurations
        And I go to the Group Configuration page in Studio
        And I work with the first group configuration
        And I see `name`, `id` are visible and have correct values
        When I expand the first group configuration
        Then I see `description` and `groups` appear and also have correct values
        And I do the same checks for the second group configuration
        """
        self.course_fix.add_advanced_settings({
            u"user_partitions": {
                "value": [
                    UserPartition(0, 'Name of the Group Configuration', 'Description of the group configuration.', [Group("0", 'Group 0'), Group("1", 'Group 1')]).to_json(),
                    UserPartition(1, 'Name of second Group Configuration', 'Second group configuration.', [Group("0", 'Alpha'), Group("1", 'Beta'), Group("2", 'Gamma')]).to_json()
                ],
            },
        })
        self.course_fix._add_advanced_settings()

        self.page.visit()

        config = self.page.group_configurations()[0]
        # no groups when the the configuration is collapsed
        self.assertEqual(len(config.groups), 0)
        self._assert_fields(
            config,
            cid="0", name="Name of the Group Configuration",
            description="Description of the group configuration.",
            groups=["Group 0", "Group 1"]
        )

        config = self.page.group_configurations()[1]

        self._assert_fields(
            config,
            name="Name of second Group Configuration",
            description="Second group configuration.",
            groups=["Alpha", "Beta", "Gamma"]
        )

    def test_can_create_and_edit_group_configuration(self):
        """
        Scenario: Ensure that the group configuration can be created and edited correctly.
        Given I have a course without group configurations
        When I click button 'Create new Group Configuration'
        And I set new name and description, change name for the 2nd default group, add one new group
        And I click button 'Create'
        Then I see the new group configuration is added and has correct data
        When I edit the group group_configuration
        And I change the name and description, add new group, remove old one and change name for the Group A
        And I click button 'Save'
        Then I see the group configuration is saved successfully and has the new data
        """
        self.page.visit()
        self.assertEqual(len(self.page.group_configurations()), 0)
        # Create new group configuration
        self.page.create()
        config = self.page.group_configurations()[0]
        config.name = "New Group Configuration Name"
        config.description = "New Description of the group configuration."
        config.groups[1].name = "New Group Name"
        # Add new group
        config.add_group()  # Group C

        # Save the configuration
        self.assertEqual(config.get_text('.action-primary'), "CREATE")
        config.save()

        self._assert_fields(
            config,
            name="New Group Configuration Name",
            description="New Description of the group configuration.",
            groups=["Group A", "New Group Name", "Group C"]
        )

        # Edit the group configuration
        config.edit()
        # Update fields
        self.assertTrue(config.id)
        config.name = "Second Group Configuration Name"
        config.description = "Second Description of the group configuration."
        self.assertEqual(config.get_text('.action-primary'), "SAVE")
        # Add new group
        config.add_group()  # Group D
        # Remove group with name "New Group Name"
        config.groups[1].remove()
        # Rename Group A
        config.groups[0].name = "First Group"
        # Save the configuration
        config.save()

        self._assert_fields(
            config,
            name="Second Group Configuration Name",
            description="Second Description of the group configuration.",
            groups=["First Group", "Group C", "Group D"]
        )

    def test_use_group_configuration(self):
        """
        Scenario: Ensure that the group configuration can be used by split_module correctly
        Given I have a course without group configurations
        When I create new group configuration
        And I set new name and add a new group, save the group configuration
        And I go to the unit page in Studio
        And I add new advanced module "Content Experiment"
        When I assign created group configuration to the module
        Then I see the module has correct groups
        And I go to the Group Configuration page in Studio
        And I edit the name of the group configuration, add new group and remove old one
        And I go to the unit page in Studio
        And I edit the unit
        Then I see the group configuration name is changed in `Group Configuration` dropdown
        And the group configuration name is changed on container page
        And I see the module has 2 active groups and one inactive
        And I see "Add missing groups" link exists
        When I click on "Add missing groups" link
        The I see the module has 3 active groups and one inactive
        """
        self.page.visit()
        # Create new group configuration
        self.page.create()
        config = self.page.group_configurations()[0]
        config.name = "New Group Configuration Name"
        # Add new group
        config.add_group()
        config.groups[2].name = "New group"
        # Save the configuration
        config.save()

        unit = self.go_to_unit_page(make_draft=True)
        add_advanced_component(unit, 0, 'split_test')
        container = self.go_to_container_page()
        container.edit()
        component_editor = ComponentEditorView(self.browser, container.locator)
        component_editor.set_select_value_and_save('Group Configuration', 'New Group Configuration Name')
        self.verify_groups(container, ['Group A', 'Group B', 'New group'], [])

        self.page.visit()
        config = self.page.group_configurations()[0]
        config.edit()
        config.name = "Second Group Configuration Name"
        # Add new group
        config.add_group()  # Group D
        # Remove Group A
        config.groups[0].remove()
        # Save the configuration
        config.save()

        container = self.go_to_container_page()
        container.edit()
        component_editor = ComponentEditorView(self.browser, container.locator)
        self.assertEqual(
            "Second Group Configuration Name",
            component_editor.get_selected_option_text('Group Configuration')
        )
        component_editor.cancel()
        self.assertIn(
            "Second Group Configuration Name",
            container.get_xblock_information_message()
        )
        self.verify_groups(
            container, ['Group B', 'New group'], ['Group A'],
            verify_missing_groups_not_present=False
        )
        # Click the add button and verify that the groups were added on the page
        container.add_missing_groups()
        self.verify_groups(container, ['Group B', 'New group', 'Group D'], ['Group A'])

    def test_can_cancel_creation_of_group_configuration(self):
        """
        Scenario: Ensure that creation of the group configuration can be canceled correctly.
        Given I have a course without group configurations
        When I click button 'Create new Group Configuration'
        And I set new name and description, add 1 additional group
        And I click button 'Cancel'
        Then I see that there is no new group configurations in the course
        """
        self.page.visit()

        self.assertEqual(len(self.page.group_configurations()), 0)
        # Create new group configuration
        self.page.create()

        config = self.page.group_configurations()[0]
        config.name = "Name of the Group Configuration"
        config.description = "Description of the group configuration."
        # Add new group
        config.add_group()  # Group C
        # Cancel the configuration
        config.cancel()

        self.assertEqual(len(self.page.group_configurations()), 0)

    def test_can_cancel_editing_of_group_configuration(self):
        """
        Scenario: Ensure that editing of the group configuration can be canceled correctly.
        Given I have a course with group configuration
        When I go to the edit mode of the group configuration
        And I set new name and description, add 2 additional groups
        And I click button 'Cancel'
        Then I see that new changes were discarded
        """
        self.course_fix.add_advanced_settings({
            u"user_partitions": {
                "value": [
                    UserPartition(0, 'Name of the Group Configuration', 'Description of the group configuration.', [Group("0", 'Group 0'), Group("1", 'Group 1')]).to_json(),
                    UserPartition(1, 'Name of second Group Configuration', 'Second group configuration.', [Group("0", 'Alpha'), Group("1", 'Beta'), Group("2", 'Gamma')]).to_json()
                ],
            },
        })
        self.course_fix._add_advanced_settings()
        self.page.visit()

        config = self.page.group_configurations()[0]

        config.name = "New Group Configuration Name"
        config.description = "New Description of the group configuration."
        # Add 2 new groups
        config.add_group()  # Group C
        config.add_group()  # Group D
        # Cancel the configuration
        config.cancel()

        self._assert_fields(
            config,
            name="Name of the Group Configuration",
            description="Description of the group configuration.",
            groups=["Group 0", "Group 1"]
        )

    def test_group_configuration_validation(self):
        """
        Scenario: Ensure that validation of the group configuration works correctly.
        Given I have a course without group configurations
        And I create new group configuration with 2 default groups
        When I set only description and try to save
        Then I see error message "Group Configuration name is required"
        When I set a name
        And I delete the name of one of the groups and try to save
        Then I see error message "All groups must have a name"
        When I delete the group without name and try to save
        Then I see error message "Please add at least two groups"
        When I add new group and try to save
        Then I see the group configuration is saved successfully
        """
        def try_to_save_and_verify_error_message(message):
             # Try to save
            config.save()
            # Verify that configuration is still in editing mode
            self.assertEqual(config.mode, 'edit')
            # Verify error message
            self.assertEqual(message, config.validation_message)

        self.page.visit()
        # Create new group configuration
        self.page.create()
        # Leave empty required field
        config = self.page.group_configurations()[0]
        config.description = "Description of the group configuration."

        try_to_save_and_verify_error_message("Group Configuration name is required")

        # Set required field
        config.name = "Name of the Group Configuration"
        config.groups[1].name = ''
        try_to_save_and_verify_error_message("All groups must have a name")
        config.groups[1].remove()
        try_to_save_and_verify_error_message("There must be at least two groups")
        config.add_group()

        # Save the configuration
        config.save()

        self._assert_fields(
            config,
            name="Name of the Group Configuration",
            description="Description of the group configuration.",
            groups=["Group A", "Group B"]
        )
