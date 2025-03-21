from odoo import http
from odoo.http import request

class BlogPostController(http.Controller):

    @http.route('/blog/get_posts', type='json', auth='user')
    def get_blog_posts(self):
        posts = request.env['blog.post'].search([], limit=10)
        return [{'id': post.id, 'name': post.name} for post in posts]
