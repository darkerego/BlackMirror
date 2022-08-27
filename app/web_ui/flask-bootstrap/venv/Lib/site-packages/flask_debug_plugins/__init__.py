from flask import render_template

from flask_debug import requires_debug


template_folder = 'templates'


def initialize_debug_ext(dbg):
    @dbg.route('/_extensions/')
    def debug_list_extensions():
        return render_template('flask_debug/plugins.html')
