/** @odoo-module **/

import { OfferButton } from "./offer_button";
import { registry } from "@web/core/registry";

export const offerButton = {
    component: OfferButton,
};

registry.category("fields").add("offer_button", offerButton);