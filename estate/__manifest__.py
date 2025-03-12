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
        
        ],
    "data": [
        "security/ir.model.access.csv",

         "views/res_partner_views.xml",
         "views/sro_contacts_work_views.xml",
         "views/sro_contacts_discipline_views.xml",
         "views/sro_contacts_inspection_views.xml",
         "views/sro_contacts_contract_views.xml",
    #    "views/res_users_views.xml",
       
    ],
    "assets": {
        "web.assets_backend": [
    #        "estate/static/src/js/offer_button.js",
    #        "estate/static/src/js/offer_button_registry.js",
    #                   
    #        
    #        "estate/static/src/js/dashboard.js",
    #        "estate/static/src/js/dashboard_registry.js",
    #        
    #        "estate/static/src/xml/offer_button.xml",
    #        "estate/static/src/xml/dashboard.xml",
    #
    #        "estate/static/src/css/dashboard.css", 
        ]
    }
}



