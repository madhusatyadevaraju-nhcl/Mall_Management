# -*- coding: utf-8 -*-
# from odoo import http


# class PurchaseIndent(http.Controller):
#     @http.route('/purchase_indent/purchase_indent', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/purchase_indent/purchase_indent/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('purchase_indent.listing', {
#             'root': '/purchase_indent/purchase_indent',
#             'objects': http.request.env['purchase_indent.purchase_indent'].search([]),
#         })

#     @http.route('/purchase_indent/purchase_indent/objects/<model("purchase_indent.purchase_indent"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('purchase_indent.object', {
#             'object': obj
#         })

