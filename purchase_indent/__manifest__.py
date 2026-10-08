# -*- coding: utf-8 -*-
{
    'name': "PurchaseIndent",

    'summary': "Short (1 phrase/line) summary of the module's purpose",

    'description': """
Long description of module's purpose
    """,

    'author': "My Company",
    'website': "https://www.yourcompany.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/15.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '0.18',

    # any module necessary for this one to work correctly
    'depends': ['base','contacts','base','purchase','rental_management','nhcl_rental_management','product'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'security/purchase_indent_groups.xml',
        'data/purchase_indent_sequence.xml',
        'data/demodata.xml',
        # 'views/views.xml',
        # 'views/templates.xml',
        'views/purchase_indent_view.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
}

