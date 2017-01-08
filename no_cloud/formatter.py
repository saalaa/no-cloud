# Copyright (C) 2016 Benoit Myard <myardbenoit@gmail.com>
# Released under the terms of the BSD license.

import markdown


def make_html(text):
    md = markdown.Markdown(extensions=[
        'markdown.extensions.extra',
        'markdown.extensions.meta',
    ])

    return md.convert(text)
