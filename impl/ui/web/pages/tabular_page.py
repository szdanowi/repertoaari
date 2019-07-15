from impl.ui.web.pages.page import Page


class TabularPage(Page):
    class ExamEntry:
        def __init__(self, id, pos, left, right, left_class, right_class, left_note=None, right_note=None):
            self.id = id
            self.pos = pos
            self.left = left or ''
            self.right = right or ''
            self.left_class = left_class
            self.right_class = right_class
            self.left_note = left_note
            self.right_note = right_note

    class DictEntry:
        def __init__(self, left, right):
            self.left = left
            self.right = right

    def display_direction(self, left_title, right_title):
        self.kwargs["left_title"] = left_title
        self.kwargs["right_title"] = right_title

    def ask_for(self, question_id, left_value, right_value):
        entries = self.kwargs.setdefault("entries", [])
        entries.append(self.ExamEntry(question_id, len(entries), left_value, right_value,
                                      'answer' if left_value is None else None,
                                      'answer' if right_value is None else None))

    def show_assessment(self, question_id, left_value, right_value, left_correct, right_correct, left_note, right_note):
        styles = {None: None, True: 'correct', False: 'wrong'}

        entries = self.kwargs.setdefault("entries", [])
        entries.append(self.ExamEntry(question_id, len(entries),
                                      left_value, right_value,
                                      styles[left_correct], styles[right_correct],
                                      left_note, right_note))

    def display_entry(self, left_value, right_value):
        entries = self.kwargs.setdefault("entries", [])
        entries.append(self.DictEntry(left_value, right_value))

    def display_summary(self, points_awarded, max_points):
        self.kwargs["points_awarded"] = points_awarded
        self.kwargs["max_points"] = max_points
        self.kwargs["grade"] = '{0:.2f}%'.format(100.0 * points_awarded / float(max_points))
