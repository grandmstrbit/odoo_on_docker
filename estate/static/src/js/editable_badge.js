/** @odoo-module */

import { registry } from "@web/core/registry";
import { useRef, useState, onMounted, Component } from "@odoo/owl";

class EditableBadge extends Component {
    setup() {
        this.selectRef = useRef("select");
        this.state = useState({ value: this.props.record.data[this.props.name] });

        onMounted(() => {
            this.updateBadgeColor();
        });
    }

    updateBadgeColor() {
        const select = this.selectRef.el;
        if (!select) return;

        const value = this.state.value;
        const badge = select.parentElement;

        badge.classList.remove("badge-success", "badge-danger", "badge-warning");

        if (value === "active") {
            badge.classList.add("badge-success");
        } else if (value === "suspended") {
            badge.classList.add("badge-danger");
        } else {
            badge.classList.add("badge-warning");
        }
    }

    onChange(ev) {
        this.state.value = ev.target.value;
        this.updateBadgeColor();
        this.props.update(ev.target.value);
    }
}

EditableBadge.template = "estate.EditableBadgeTemplate"; // Указываем XML-шаблон

registry.category("fields").add("editable_badge", EditableBadge);
