from impl.ui.web.pages.page import Page


class ErrorPage(Page):
    def display_error(self, error):
        self.kwargs["error"] = error
        return self
