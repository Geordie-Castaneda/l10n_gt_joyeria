from odoo import _, fields, models


class StockPicking(models.Model):
    _inherit = "stock.picking"

    credit_note_id = fields.Many2one(
        "account.move",
        string="Nota de crédito relacionada",
        copy=False,
        index=True,
        readonly=True,
    )
    credit_note_validation_logged = fields.Boolean(copy=False, readonly=True)

    def _action_done(self):
        result = super()._action_done()
        completed_returns = self.filtered(
            lambda picking: picking.credit_note_id
            and picking.state == "done"
            and not picking.credit_note_validation_logged
        )
        for picking in completed_returns:
            user_name = self.env.user.display_name
            message = _(
                "Devolución %(picking)s vinculada a la nota %(move)s validada por %(user)s.",
                picking=picking.name,
                move=picking.credit_note_id.display_name,
                user=user_name,
            )
            picking.message_post(body=message)
            picking.credit_note_id.sudo().message_post(body=message)
            picking.credit_note_validation_logged = True
        return result
