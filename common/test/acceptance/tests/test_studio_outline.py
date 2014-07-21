"""
Acceptance tests for studio related to the outline page.
"""

from ..pages.studio.auto_auth import AutoAuthPage
from ..pages.studio.overview import CourseOutlinePage, ContainerPage
from ..fixtures.course import CourseFixture, XBlockFixtureDesc

from helpers import StudioCourseTest


class CourseOutlineTest(StudioCourseTest):
    """
    Tests that verify the sections name editable only inside headers in Sutdio Course Outline that you can get to
    when logged in and have a course.
    """

    COURSE_ID_SEPARATOR = "."

    def setUp(self):
        """
        Install a course with no content using a fixture.
        """
        super(CourseOutlineTest, self).setUp()
        self.auth_page = AutoAuthPage(self.browser, staff=True).visit()
        self.course_outline_page = CourseOutlinePage(
            self.browser, self.course_info['org'], self.course_info['number'], self.course_info['run']
        )

    def populate_course_fixture(self, course_fixture):
        """ Install a course with sections/problems, tabs, updates, and handouts """
        course_fixture.add_children(
            XBlockFixtureDesc('chapter', 'Test Section').add_children(
                XBlockFixtureDesc('sequential', 'Test Subsection').add_children(
                    XBlockFixtureDesc('vertical', 'Test Unit')
                )
            )
        )


class EditNamesTest(CourseOutlineTest):
    """
    Feature: Click-to-edit section/subsection names
    """

    __test__ = True

    def set_name_and_verify(self, item, old_name, new_name, expected_name):
        self.assertEqual(item.name, old_name)
        item.change_name(new_name)
        self.assertFalse(item.in_editable_form())
        self.assertEqual(item.name, expected_name)

    def test_edit_section_name(self):
        """
        Scenario: Click-to-edit section name
            Given that I have created a section
            When I click on the name of section
            Then the section name becomes editable
            And given that I have edited the section name
            When I click outside of the edited section name
            Then the section name saves
            And becomes non-editable
        """
        self.course_outline_page.visit()
        self.set_name_and_verify(
            self.course_outline_page.section_at(0),
            'Test Section',
            'Changed',
            'Changed'
        )

    def test_edit_subsection_name(self):
        """
        Scenario: Click-to-edit subsection name
            Given that I have created a subsection
            When I click on the name of subsection
            Then the subsection name becomes editable
            And given that I have edited the subsection name
            When I click outside of the edited subsection name
            Then the subsection name saves
            And becomes non-editable
        """
        self.course_outline_page.visit()
        self.set_name_and_verify(
            self.course_outline_page.section_at(0).subsection_at(0),
            'Test Subsection',
            'Changed',
            'Changed'
        )


    def test_edit_empty_section_name(self):
        """
        Scenario: Click-to-edit section name, enter empty name
            Given that I have crate a section
            And I have clicked to edit the name of the section
            And I have entered an empty section name
            When I click outside of the edited section name
            Then the section name does not change
            And becomes non-editable
        """
        self.course_outline_page.visit()
        self.set_name_and_verify(
            self.course_outline_page.section_at(0),
            'Test Section',
            '',
            'Test Section'
        )

    def test_edit_empty_subsection_name(self):
        """
        Scenario: Click-to-edit subsection name, enter empty name
            Given that I have created a subsection
            And I have clicked to edit the name of the subsection
            And I have entered an empty subsection name
            When I click outside of the edited subsection name
            Then the subsection name does not change
            And becomes non-editable
        """
        self.course_outline_page.visit()
        self.set_name_and_verify(
            self.course_outline_page.section_at(0).subsection_at(0),
            'Test Subsection',
            '',
            'Test Subsection'
        )

    # TODO: reenable when release date support is added back
    # def test_section_name_not_editable_inside_modal(self):
    #     """
    #     Check that the section name is not editable inside "Section Release Date" modal on course outline page.
    #     """
    #     parent_css = 'div.modal-window'
    #     self.course_outline_page.click_release_date()
    #     section_name = self.course_outline_page.get_section_name(parent_css)[0]
    #     self.assertEqual(section_name, '"Test Section"')
    #     self.course_outline_page.click_section_name(parent_css)
    #     section_name_edit_form = self.course_outline_page.section_name_edit_form_present(parent_css)
    #     self.assertFalse(section_name_edit_form)


class CreateSectionsTest(CourseOutlineTest):
    """
    Feature: Create new sections/subsections/units
    """

    __test__ = True

    def populate_course_fixture(self, course_fixture):
        """ Start with a completely empty course to easily test adding things to it """
        pass

    def test_create_new_section_from_top_button(self):
        """
        Scenario: Create new section from button at top of page
            Given that I am on the course outline
            When I click the "+ Add section" button at the top of the page
            Then I see a new section added to the bottom of the page
            And the display name is in its editable form.
        """
        self.course_outline_page.visit()
        self.course_outline_page.add_section_from_top_button()
        self.assertEqual(len(self.course_outline_page.sections()), 1)
        self.assertTrue(self.course_outline_page.section_at(0).in_editable_form())

    def test_create_new_section_from_bottom_button(self):
        """
        Scenario: Create new section from button at bottom of page
            Given that I am on the course outline
            When I click the "+ Add section" button at the bottom of the page
            Then I see a new section added to the bottom of the page
            And the display name is in its editable form.
        """
        self.course_outline_page.visit()
        self.course_outline_page.add_section_from_bottom_button()
        self.assertEqual(len(self.course_outline_page.sections()), 1)
        self.assertTrue(self.course_outline_page.section_at(0).in_editable_form())

    def test_create_new_subsection(self):
        """
        Scenario: Create new subsection
            Given that I have created a section
            When I click the "+ Add subsection" button in that section
            Then I see a new subsection added to the bottom of the section
            And the display name is in its editable form.
        """
        self.course_outline_page.visit()
        self.course_outline_page.add_section_from_top_button()
        self.assertEqual(len(self.course_outline_page.sections()), 1)
        self.course_outline_page.section_at(0).add_subsection()
        subsections = self.course_outline_page.section_at(0).subsections()
        self.assertEqual(len(subsections), 1)
        self.assertTrue(subsections[0].in_editable_form())

    def test_create_new_unit(self):
        """
        Scenario: Create new unit
            Given that I have created a section
            And that I have created a subsection within that section
            When I click the "+ Add unit" button in that subsection
            Then I am redirected to a New Unit page
            And the display name is in its editable form.
        """
        self.course_outline_page.visit()
        self.course_outline_page.add_section_from_top_button()
        self.assertEqual(len(self.course_outline_page.sections()), 1)
        self.course_outline_page.section_at(0).add_subsection()
        self.assertEqual(len(self.course_outline_page.section_at(0).subsections()), 1)
        self.course_outline_page.section_at(0).subsection_at(0).add_unit()
        unit_page = ContainerPage(self.browser, None)
        self.assertTrue(unit_page.display_name_in_editable_form())


class DeleteContentTest(CourseOutlineTest):
    """
    Feature: Deleting sections/subsections/units
    """

    __test__ = True

    def test_delete_section(self):
        """
        Scenario: Delete section
            Given that I am on the course outline
            When I click the delete button for a section on the course outline
            Then I should receive a confirmation message, asking me if I really want to delete the section
            When I click "Yes, I want to delete this component"
            Then the confirmation message should close
            And the section should immediately be deleted from the course outline
        """
        self.course_outline_page.visit()
        self.assertEqual(len(self.course_outline_page.sections()), 1)
        self.course_outline_page.section_at(0).delete()
        self.assertEqual(len(self.course_outline_page.sections()), 0)

    def test_cancel_delete_section(self):
        """
        Scenario: Cancel delete of section
            Given that I clicked the delte button for a section on the course outline
            And I received a confirmation message, asking me if I really want to delete the component
            When I click "Cancel"
            Then the confirmation message should close
            And the section should remain in the course outline
        """
        self.course_outline_page.visit()
        self.assertEqual(len(self.course_outline_page.sections()), 1)
        self.course_outline_page.section_at(0).delete(cancel=True)
        self.assertEqual(len(self.course_outline_page.sections()), 1)

    def test_delete_subsection(self):
        """
        Scenario: Delete subsection
            Given that I am on the course outline
            When I click the delete button for a subsection on the course outline
            Then I should receive a confirmation message, asking me if I really want to delte the subsection
            When I click "Yes, I want to delete this component"
            Then the confiramtion message should close
            And the subsection should immediately be deleted from the course outline
        """
        self.course_outline_page.visit()
        self.assertEqual(len(self.course_outline_page.section_at(0).subsections()), 1)
        self.course_outline_page.section_at(0).subsection_at(0).delete()
        self.assertEqual(len(self.course_outline_page.section_at(0).subsections()), 0)


    def test_cancel_delete_subsection(self):
        """
        Scenario: Cancel delete of subsection
            Given that I clicked the delete button for a subsection on the course outline
            And I received a confirmation message, asking me if I really want to delete the subsection
            When I click "cancel"
            Then the confirmation message should close
            And the subsection should remain in the course outline
        """
        self.course_outline_page.visit()
        self.assertEqual(len(self.course_outline_page.section_at(0).subsections()), 1)
        self.course_outline_page.section_at(0).subsection_at(0).delete(cancel=True)
        self.assertEqual(len(self.course_outline_page.section_at(0).subsections()), 1)

    def test_delete_unit(self):
        """
        Scenario: Delete unit
            Given that I am on the course outline
            When I click the delete button for a unit on the course outline
            Then I should receive a confirmation message, asking me if I really want to delete the unit
            When I click "Yes, I want to delete this unit"
            Then the confirmation message should close
            And the unit should immediately be deleted from the course outline
        """
        self.course_outline_page.visit()
        self.course_outline_page.section_at(0).subsection_at(0).toggle_expand()
        self.assertEqual(len(self.course_outline_page.section_at(0).subsection_at(0).units()), 1)
        self.course_outline_page.section_at(0).subsection_at(0).unit_at(0).delete()
        self.assertEqual(len(self.course_outline_page.section_at(0).subsection_at(0).units()), 0)

    def test_cancel_delete_unit(self):
        """
        Scenario: Cancel delete of unit
            Given that I clicked the delete button for a unit on the course outline
            And I received a confiramtion message, asking me if I really want to delete the unit
            When I click "Cancel"
            Then the confiramtion message should close
            And the unit should remain in the course outline
        """
        self.course_outline_page.visit()
        self.course_outline_page.section_at(0).subsection_at(0).toggle_expand()
        self.assertEqual(len(self.course_outline_page.section_at(0).subsection_at(0).units()), 1)
        self.course_outline_page.section_at(0).subsection_at(0).unit_at(0).delete(cancel=True)
        self.assertEqual(len(self.course_outline_page.section_at(0).subsection_at(0).units()), 1)

    def test_delete_all_no_content_message(self):
        """
        Scenario: Delete all sections/subsections/units in a course, "no content" message should appear
            Given that I delete all sections, subsections, and units in a course
            When I visit the course outline
            Then I will see a message that says, "You haven't added any content to this course yet"
            Add see a + Add Section button
        """
        self.course_outline_page.visit()
        self.assertFalse(self.course_outline_page.has_no_content_message)
        self.course_outline_page.section_at(0).delete()
        self.assertEqual(len(self.course_outline_page.sections()), 0)
        self.assertTrue(self.course_outline_page.has_no_content_message)
