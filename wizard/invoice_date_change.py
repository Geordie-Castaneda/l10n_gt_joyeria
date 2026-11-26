from odoo import _, fields, models
from odoo.exceptions import AccessError, UserError


class InvoiceDateChangeWizard(models.TransientModel):
    _name = "l10n_gt_joyeria.invoice_date_change_wizard"
    _description = "Confirmación de cambio de fecha de factura"

    move_id = fields.Many2one("account.move", required=True, readonly=True)
    current_invoice_date = fields.Date(string="Fecha actual", required=False, readonly=True)
    new_invoice_date = fields.Date(string="Nueva fecha", required=True)
    change_reason = fields.Char(string="Motivo del cambio")

    def action_confirm_date_change(self):
        self.ensure_one()
        if not self.env.user.has_group("account.group_account_manager"):
            raise AccessError(_("Solo un responsable de contabilidad puede cambiar la fecha."))

        move = self.move_id
        if move.state != "posted" or move.move_type not in ("out_invoice", "out_refund"):
            raise UserError(_("Solo se puede cambiar la fecha de facturas de cliente publicadas."))
        if move.invoice_date != self.current_invoice_date:
            raise UserError(_("La fecha de la factura cambió. Cierra y vuelve a abrir el asistente."))
        if move.invoice_date == self.new_invoice_date:
            raise UserError(_("La nueva fecha debe ser distinta de la fecha actual."))

        old_date = fields.Date.to_string(move.invoice_date) if move.invoice_date else _("Sin fecha")
        new_date = fields.Date.to_string(self.new_invoice_date)
        user_name = self.env.user.display_name
        print(
            f"[JOYERIA] Cambio de fecha solicitado para {move.name} (ID {move.id}) "
            f"por {user_name}: {old_date} -> {new_date}",
            flush=True,
        )

        # Se omite la restricción de solo lectura únicamente para actualizar invoice_date.
        move.with_context(skip_readonly_check=True).write({
            "invoice_date": self.new_invoice_date,
        })

        message = _(
            "Fecha de factura cambiada de %(old_date)s a %(new_date)s por %(user)s.",
            old_date=old_date,
            new_date=new_date,
            user=user_name,
        )
        if self.change_reason:
            message = "%s\n%s" % (message, _("Motivo: %s", self.change_reason))
        move.message_post(body=message, message_type="comment", subtype_xmlid="mail.mt_note")

        notification = _(
            "La fecha en Odoo se cambió de %(old_date)s a %(new_date)s. "
            "El documento FEL no fue modificado; verifique que la fecha coincida con la registrada en FEL.",
            old_date=old_date,
            new_date=new_date,
        )
        print(f"[JOYERIA] Fecha de {move.name} actualizada y registrada en el chatter", flush=True)
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Fecha actualizada"),
                "message": notification,
                "type": "warning",
                "sticky": True,
                "next": {"type": "ir.actions.act_window_close"},
            },
        }
