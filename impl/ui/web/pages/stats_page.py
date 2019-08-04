from impl.ui.web.pages.page import Page


class StatsPage(Page):
    def __init__(self):
        Page.__init__(self, 'stats.html')

    class DictEntry:
        def __init__(self, left, right, label, percentage):
            self.left = left
            self.right = right
            self.label = label
            self.percentage = percentage
            self.percentage_wrong = 100.0 - percentage if percentage else None

    def display_direction(self, left_title, right_title):
        self.kwargs["left_title"] = left_title
        self.kwargs["right_title"] = right_title

    def display_entry(self, left_value, right_value, correct='', total='', percentage=None):
        entries = self.kwargs.setdefault("entries", [])
        entries.append(self.DictEntry(left_value, right_value, '{0}/{1}'.format(correct, total), percentage))
