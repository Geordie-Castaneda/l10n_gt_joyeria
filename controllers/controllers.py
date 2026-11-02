# -*- coding: utf-8 -*-
# from odoo import http


# class L10nGtJoyeria(http.Controller):
#     @http.route('/l10n_gt_joyeria/l10n_gt_joyeria', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/l10n_gt_joyeria/l10n_gt_joyeria/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('l10n_gt_joyeria.listing', {
#             'root': '/l10n_gt_joyeria/l10n_gt_joyeria',
#             'objects': http.request.env['l10n_gt_joyeria.l10n_gt_joyeria'].search([]),
#         })

#     @http.route('/l10n_gt_joyeria/l10n_gt_joyeria/objects/<model("l10n_gt_joyeria.l10n_gt_joyeria"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('l10n_gt_joyeria.object', {
#             'object': obj
#         })

