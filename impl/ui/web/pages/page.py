from flask import url_for, render_template


class Page:
    def __init__(self, template):
        self.template = template
        self.kwargs = dict()
        self.kwargs['stylesheet'] = url_for('static', filename='style.css')

    def render(self):
        return render_template(self.template, **self.kwargs)

    def display_dictionary_name(self, name):
        self.kwargs["dict_name"] = name
        self.kwargs["dict_href"] = url_for('show_dictionary_listing', dict_file=name)
        self.kwargs["exam_href"] = url_for('show_exam', dict_file=name, words=12)
        return self
