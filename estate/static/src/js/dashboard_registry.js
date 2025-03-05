/** @odoo-module **/

import { EstateDashboard } from "./dashboard";
import { registry } from "@web/core/registry";

export const estateDashboard = {
    component: EstateDashboard,
};

registry.category("actions").add("estate_dashboard", estateDashboard);