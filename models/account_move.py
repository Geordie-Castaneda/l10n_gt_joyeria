from odoo import models, _
from odoo.exceptions import UserError


class AccountMove(models.Model):
    _inherit = "account.move"

    def action_post(self):
        credit_notes = self.filtered(lambda move: move.move_type == "out_refund")
        if credit_notes and not self.env.context.get("skip_credit_note_return_wizard"):
            if len(self) > 1:
                raise UserError(
                    _("Confirma las notas de crédito de una en una para elegir sus devoluciones de inventario.")
                )
            move = credit_notes
            sale_lines = move.invoice_line_ids.sale_line_ids
            sale_lines |= move.reversed_entry_id.invoice_line_ids.sale_line_ids
            pickings = sale_lines.order_id.picking_ids.filtered(
                lambda picking: picking.state == "done"
                and picking.picking_type_code == "outgoing"
                and picking.location_dest_id.usage == "customer"
            )
            picking_lines = []
            for picking in pickings:
                move_lines = []
                for stock_move in picking.move_ids.filtered(
                    lambda stock_move: stock_move.state == "done"
                    and not stock_move.scrapped
                    and stock_move.location_id.usage == "internal"
                    and stock_move.location_dest_id.usage == "customer"
                ):
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
                    qty_available = max(delivered_qty - already_returned, 0.0)
                    if qty_available:
                        move_lines.append((0, 0, {
                            "stock_move_id": stock_move.id,
                            "quantity_available": qty_available,
                            "quantity_to_return": qty_available,
                        }))
                if move_lines:
                    picking_lines.append((0, 0, {
                        "picking_id": picking.id,
                        "move_line_ids": move_lines,
                    }))

            if picking_lines:
                wizard = self.env["l10n_gt_joyeria.credit_note_return_wizard"].create({
                    "move_id": move.id,
                    "picking_line_ids": picking_lines,
                })
                return {
                    "type": "ir.actions.act_window",
                    "name": _("Devoluciones relacionadas"),
                    "res_model": "l10n_gt_joyeria.credit_note_return_wizard",
                    "res_id": wizard.id,
                    "view_mode": "form",
                    "target": "new",
                }
        return super().action_post()
