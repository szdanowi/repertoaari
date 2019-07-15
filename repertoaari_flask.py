from flask import Flask, request

from impl.ui.web.pages import *
from repertoaari import NoSuchDictionary, Repertoaari, FlashContext, InvalidRequest

flask_app = Flask(__name__)
repertoaari = Repertoaari()


@flask_app.route("/")
def hello():
    return "Hello, World!"


@flask_app.errorhandler(404)
def on_page_not_found(error):
    return ErrorPage('page_not_found.html').display_error('{0} {1}'.format(request.method, request.path)).render(), 404


@flask_app.errorhandler(500)
def on_server_error(error):
    return ErrorPage('error.html').display_error(error.description).render(), 500


@flask_app.errorhandler(InvalidRequest)
def on_invalid_request(error):
    return ErrorPage('error.html').display_error(error).render(), 400


@flask_app.errorhandler(NoSuchDictionary)
def on_invalid_dictionary(error):
    return on_page_not_found(error)


@flask_app.route("/<dict_file>/list")
def show_dictionary_listing(dict_file):
    return repertoaari.show_dictionary(TabularPage('listing.html'), dict_file).render()


@flask_app.route("/<dict_file>/exam/random-<int:words>", methods=['GET'])
def show_exam(dict_file, words):
    return repertoaari.show_exam(TabularPage('exam.html'), dict_file, words).render()


@flask_app.route("/<dict_file>/exam/random-<int:words>", methods=['POST'])
def assess_exam(dict_file, words):
    answers = []
    for key in sorted(request.form.keys()):
        if key.strip().startswith('answer_'):
            elements = key.strip().split('_')
            answers.append(Repertoaari.Answer(elements[2], elements[3], request.form[key]))

    return repertoaari.assess_exam(TabularPage('exam.html'), dict_file, answers).render()


@flask_app.route("/<dict_file>/flash", methods=['GET', 'POST'])
def show_flash(dict_file):
    page = FlashPage('flash.html').with_next('show_assess_flash', dict_file=dict_file)
    context = FlashContext.from_str(request.form.get('context'))

    return repertoaari.show_flash(page, dict_file, context).render()


@flask_app.route("/<dict_file>/assess_flash", methods=['POST'])
def show_assess_flash(dict_file):
    page = FlashPage('flash.html').with_next('show_flash', dict_file=dict_file)
    context = FlashContext.from_str(request.form.get('context'))

    return repertoaari.assess_flash(page, dict_file, request.form['id'], request.form['answer'], context).render()
