# © 2024 initOS GmbH
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo.http import Controller, request, route

from odoo.addons.mass_mailing.controllers.main import MassMailController


class MassMailController(MassMailController):
    @route("/website_mass_mailing/subscribe", type="json", website=True, auth="public")
    def subscribe(self, list_id, email, **post):
        if not request.env["ir.http"]._verify_request_recaptcha_token(
            "website_mass_mailing_double_opt_in"
        ):
            return {
                "toast_type": "danger",
                "toast_content": ("Suspicious activity detected by Google reCaptcha."),
            }

        subscription = request.env["mailing.contact.subscription"].sudo()
        # add email to session
        request.session["mass_mailing_email"] = subscription.double_opt_in_subscribe(
            list_id,
            email,
            language=post.get("language") or request.lang.code,
        )

        return {
            "toast_type": "success",
            "toast_content": ("Thanks for subscribing!"),
        }


class ConsentController(Controller):
    def consent_success(self):
        """Successful consent to redirect to different sides if required"""
        base_url = request.httprequest.base_url
        base_url += "/subscribed"
        return request.redirect(base_url)

    def consent_failure(self):
        return request.render(
            "website_mass_mailing_double_opt_in.invalid_subscription_confirmation_template"
        )

    @route("/subscribed", type="http", auth="public", website=True)
    def subscribed(self, **kwargs):
        return request.render("website_mass_mailing_double_opt_in.subscribe")

    @route(
        "/newsletter/confirmation/<access_token>",
        type="http",
        auth="none",
        website=True,
    )
    def consent(self, access_token, **kwargs):
        mailing_list_contact = (
            request.env["mailing.contact.subscription"]
            .sudo()
            .search([("access_token", "=", access_token)])
        )
        if mailing_list_contact:
            mailing_list_contact.write({"opt_out": False})
            template = mailing_list_contact.consent_mail_template().sudo()
            template.with_context(lang=mailing_list_contact.mail_language).send_mail(
                mailing_list_contact.id, force_send=True
            )

            return self.consent_success()

        return self.consent_failure()
