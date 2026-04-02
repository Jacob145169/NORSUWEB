from django.contrib import messages


class UserFormKwargsMixin:
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs


class SuccessMessageMixin:
    success_message = ""

    def form_valid(self, form):
        if self.success_message:
            messages.success(self.request, self.success_message)
        return super().form_valid(form)


class PageMetadataMixin:
    dashboard_title = ""
    page_title = ""
    page_description = ""
    submit_label = ""

    def get_dashboard_title(self):
        return self.dashboard_title

    def get_page_title(self):
        return self.page_title

    def get_page_description(self):
        return self.page_description

    def get_submit_label(self):
        return self.submit_label

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        dashboard_title = self.get_dashboard_title()
        page_title = self.get_page_title()
        page_description = self.get_page_description()
        submit_label = self.get_submit_label()

        if dashboard_title:
            context["dashboard_title"] = dashboard_title
        if page_title:
            context["page_title"] = page_title
        if page_description:
            context["page_description"] = page_description
        if submit_label:
            context["submit_label"] = submit_label

        return context
