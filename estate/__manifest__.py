{
    "name": "Real Estate",
    "author": "Asoft21",
    'website': 'https://asoft21.ru',
    'version': '17.0.1.0.0',
    "license": "LGPL-3",
    "category": "Contacts",
    'website': 'https://asoft21.ru',
    "summary": "SRO Contacts",
    "application": True, 
    "depends": [
        "hr",
        ],
    "data": [
        "security/ir.model.access.csv",

         "views/res_partner_views.xml",
         "views/sro_contacts_work_views.xml",
         "views/sro_contacts_discipline_views.xml",
         "views/sro_contacts_inspection_views.xml",
         "views/sro_contacts_contract_views.xml",
         "views/sro_contacts_construction.xml",
         "views/hr_employee.xml",

       
    ],
    "assets": {
        "web.assets_backend": [
        #    "estate/static/src/js/editable_badge.js",
        #    "estate/static/src/css/editable_badge.css",
        #    "estate/static/src/xml/editable_badge.xml",
        ]
    }
}



