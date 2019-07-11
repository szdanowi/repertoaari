from flask import Flask, render_template, url_for, abort, request
from repertoaari import CachedDictionaries, NoSuchDictionary, Repertoaari

flask_app = Flask(__name__)
dictionaries = CachedDictionaries()
repertoaari = Repertoaari(dictionaries)


@flask_app.route("/")
def hello():
    return "Hello, World!"


@flask_app.errorhandler(404)
def page_not_found(error):
    return render_template(
        'page_not_found.html',
        stylesheet=url_for('static', filename='style.css'),
        path=request.path,
        method=request.method
    ), 404


@flask_app.errorhandler(500)
def page_not_found(error):
    return render_template(
        'internal_server_error.html',
        stylesheet=url_for('static', filename='style.css'),
        error=error.description
    ), 500


@flask_app.route("/<dict_file>/list")
def show_dictionary_listing(dict_file):
    try:
        selected = dictionaries.load(dict_file + '.dict')

        return render_template(
            'listing.html',
            stylesheet=url_for('static', filename='style.css'),
            dict_file=dict_file,
            head=[selected.left, selected.right],
            entries=[[e.word, e.accepted()] for e in selected])

    except NoSuchDictionary:
        abort(404)


class ExamUserInterface:
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

    def __init__(self):
        self.kwargs = dict()

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

    def display_summary(self, points_awarded, max_points):
        self.kwargs["points_awarded"] = points_awarded
        self.kwargs["max_points"] = max_points
        self.kwargs["grade"] = '{0:.2f}%'.format(100.0 * points_awarded / float(max_points))


@flask_app.route("/<dict_file>/exam/random-<int:words>", methods=['GET'])
def show_exam_ltr(dict_file, words):
    try:
        page = ExamUserInterface()

        dictionary = dictionaries.load(dict_file + '.dict')
        repertoaari.show_left_to_right_exam(page, dictionary, words)

        return render_template(
            'exam.html',
            stylesheet=url_for('static', filename='style.css'),
            **page.kwargs)

    except RuntimeError as e:
        abort(500, str(e))

    except NoSuchDictionary:
        abort(404)


@flask_app.route("/<dict_file>/exam/random-<int:words>", methods=['POST'])
def assess_exam_ltr(dict_file, words):
    try:
        page = ExamUserInterface()

        answers = []
        for key in sorted(request.form.keys()):
            if key.strip().startswith('answer_'):
                elements = key.strip().split('_')
                answers.append(Repertoaari.Answer(elements[2], elements[3], request.form[key]))

        dictionary = dictionaries.load(dict_file + '.dict')
        repertoaari.assess_exam(page, dictionary, answers)
        return render_template(
            'exam.html',
            stylesheet=url_for('static', filename='style.css'),
            **page.kwargs)

    except RuntimeError as e:
        abort(500, str(e))

    except NoSuchDictionary:
        abort(404)