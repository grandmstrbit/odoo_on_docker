/** @odoo-module */
import { registry } from "@web/core/registry";
import { Many2OneField } from "@web/views/fields/many2one/many2one_field";
import { useState } from "@odoo/owl";

class BlogPostSelector extends Many2OneField {
    setup() {
        super.setup();
        this.state = useState({
            selectedPost: this.props.value || null,
            choices: [],
        });
        this.loadBlogPosts();
    }

    async loadBlogPosts() {
        // Загружаем список блогов через RPC-запрос
        this.state.choices = await this.rpc("/blog/get_posts", {});
        this.render();
    }

    onPostSelected(event) {
        this.state.selectedPost = event.target.value;
        this.value = this.state.selectedPost;  // Устанавливаем значение Many2One
    }

    get blogUrl() {
        return this.state.selectedPost ? `/blog/${this.state.selectedPost}` : "";
    }
}

// Регистрируем как "field", а не "view"
registry.category("fields").add("blog_post_selector", BlogPostSelector);
