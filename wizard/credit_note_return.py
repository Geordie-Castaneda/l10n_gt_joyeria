from odoo import _, fields, models
from odoo.exceptions import UserError
from odoo.tools.float_utils import float_compare
from markupsafe import Markup


class CreditNoteReturnWizard(models.TransientModel):
    _name = "l10n_gt_joyeria.credit_note_return_wizard"
    _description = "Devoluciones de inventario relacionadas con nota de crédito"

    move_id = fields.Many2one("account.move", required=True, readonly=True)
    picking_line_ids = fields.One2many(
        "l10n_gt_joyeria.credit_note_return_picking_line",
        "wizard_id",
        string="Entregas vinculadas",
    )

    def action_confirm_note_only(self):
        self.ensure_one()
        move = self.move_id
        move.with_context(skip_credit_note_return_wizard=True).action_post()
        source_pickings = ", ".join(self.picking_line_ids.mapped("picking_id.name"))
        move.message_post(
            body=_(
                "Nota de crédito confirmada por %(user)s sin crear devoluciones de inventario. "
                "Entregas revisadas: %(pickings)s.",
                user=self.env.user.display_name,
                pickings=source_pickings,
            )
        )
        return {"type": "ir.actions.act_window_close"}

    def action_confirm_with_returns(self):
        self.ensure_one()
        selected_lines = self.picking_line_ids.mapped("move_line_ids").filtered("selected")
        return_all = not selected_lines
        if return_all:
            selected_lines = self.picking_line_ids.mapped("move_line_ids")

        for line in selected_lines:
            stock_move = line.stock_move_id
            delivered_qty = stock_move.product_uom._compute_quantity(
                stock_move.quantity, stock_move.product_id.uom_id
            )
            already_returned = sum(
                returned_move.product_uom._compute_quantity(
                    returned_move.quantity, stock_move.product_id.uom_id
                )
                for returned_move in stock_move.returned_move_ids
                if returned_move.state != "cancel"
            )
            still_returnable = max(delivered_qty - already_returned, 0.0)
            if float_compare(
                line.quantity_to_return,
                still_returnable,
                precision_rounding=stock_move.product_id.uom_id.rounding,
            ) > 0:
                raise UserError(_(
                    "La cantidad disponible para devolver de %(product)s cambió. "
                    "Cierra este asistente y vuelve a abrirlo.",
                    product=line.product_id.display_name,
                ))

        move = self.move_id
        move.with_context(skip_credit_note_return_wizard=True).action_post()
        return_pickings = self.env["stock.picking"]

        for picking_line in self.picking_line_ids:
            selected_move_lines = (
                picking_line.move_line_ids if return_all
                else picking_line.move_line_ids.filtered("selected")
            )
            if not selected_move_lines:
                continue
            return_wizard = self.env["stock.return.picking"].with_context(
                active_model="stock.picking",
                active_id=picking_line.picking_id.id,
                active_ids=[picking_line.picking_id.id],
            ).create({"picking_id": picking_line.picking_id.id})
            for line in selected_move_lines:
                return_line = return_wizard.product_return_moves.filtered(
                    lambda candidate: candidate.move_id == line.stock_move_id
                )
                if not return_line:
                    raise UserError(_("No se encontró el producto %(product)s en la entrega %(picking)s.",
                                      product=line.product_id.display_name,
                                      picking=picking_line.picking_id.name))
                return_line.quantity = line.quantity_to_return

            action = return_wizard.action_create_returns()
            return_picking = self.env["stock.picking"].browse(action["res_id"])
            return_picking.credit_note_id = move
            return_pickings |= return_picking

        if return_pickings:
            base_url = self.env["ir.config_parameter"].sudo().get_param("web.base.url")
            source_picking_lines = self.picking_line_ids if return_all else self.picking_line_ids.filtered(
                lambda picking_line: picking_line.move_line_ids.filtered("selected")
            )
            source_pickings = ", ".join(source_picking_lines.mapped("picking_id.name"))
            picking_links = Markup(", ").join(
                Markup('<a href="%s/web#id=%s&amp;model=stock.picking&amp;view_type=form">%s</a>')
                % (base_url, picking.id, picking.name)
                for picking in return_pickings
            )
            note = Markup(_(
                "Nota de crédito confirmada por %(user)s. Se crearon las devoluciones %(pickings)s; "
                "provienen de las entregas %(sources)s. Valida las transferencias para actualizar el inventario.",
            )) % {
                "user": self.env.user.display_name,
                "pickings": picking_links,
                "sources": source_pickings,
            }
            move.message_post(body=note)
            for picking in return_pickings:
                picking.message_post(
                    body=_("Devolución creada desde la nota de crédito %(move)s.", move=move.display_name)
                )
            if len(return_pickings) == 1:
                return {
                    "type": "ir.actions.act_window",
                    "name": _("Transferencia de devolución"),
                    "res_model": "stock.picking",
                    "res_id": return_pickings.id,
                    "view_mode": "form",
                    "target": "current",
                }
            return {
                "type": "ir.actions.act_window",
                "name": _("Transferencias de devolución"),
                "res_model": "stock.picking",
                "view_mode": "list,form",
                "domain": [("id", "in", return_pickings.ids)],
                "target": "current",
            }
        return {"type": "ir.actions.act_window_close"}


class CreditNoteReturnPickingLine(models.TransientModel):
    _name = "l10n_gt_joyeria.credit_note_return_picking_line"
    _description = "Entrega disponible para devolución desde nota de crédito"

    wizard_id = fields.Many2one(
        "l10n_gt_joyeria.credit_note_return_wizard", required=True, ondelete="cascade"
    )
    picking_id = fields.Many2one("stock.picking", string="Entrega", required=True, readonly=True)
    date_done = fields.Datetime(related="picking_id.date_done", string="Fecha", readonly=True)
    origin = fields.Char(related="picking_id.origin", readonly=True)
    move_line_ids = fields.One2many(
        "l10n_gt_joyeria.credit_note_return_move_line",
        "picking_line_id",
        string="Productos entregados",
    )


class CreditNoteReturnMoveLine(models.TransientModel):
    _name = "l10n_gt_joyeria.credit_note_return_move_line"
    _description = "Producto disponible para devolución desde nota de crédito"

    picking_line_id = fields.Many2one(
        "l10n_gt_joyeria.credit_note_return_picking_line", required=True, ondelete="cascade"
    )
    selected = fields.Boolean(string="Devolver")
    stock_move_id = fields.Many2one("stock.move", required=True, readonly=True)
    product_id = fields.Many2one(related="stock_move_id.product_id", string="Producto", readonly=True)
    quantity_available = fields.Float(string="Pendiente de devolución", readonly=True)
    quantity_to_return = fields.Float(string="Cantidad a devolver", required=True, readonly=True)
    uom_id = fields.Many2one(related="product_id.uom_id", string="Unidad", readonly=True)
