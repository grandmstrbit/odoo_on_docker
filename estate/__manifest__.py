{
    "name": "Real Estate",
    "author": "Asoft21",
    'website': 'https://asoft21.ru',
    'version': '17.0.1.0.0',
    "license": "LGPL-3",
    "category": "Contacts",
    "summary": "SRO Contacts",
    "application": True, 
    "depends": [
        "hr",
        "website_blog",
        "web"
        ],
    "data": [
        "security/ir.model.access.csv",

         "views/res_partner_views.xml",
        # "views/sro_admission_basis_template.xml",
         "views/sro_contacts_work_views.xml",
         "views/sro_contacts_discipline_views.xml",
         "views/sro_contacts_inspection_views.xml",
         "views/sro_contacts_contract_views.xml",
         "views/sro_contacts_construction.xml",
         "views/hr_employee.xml",
         "views/sro_contacts_inspection_menu.xml",

       
    ],
    "assets": {
        "web.assets_backend": [
        #    "estate/static/src/js/sro_admission_basis.js",
        #    "estate/static/src/xml/sro_admission_basis_render.xml",
        ]
    }
}



