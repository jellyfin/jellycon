from html.parser import HTMLParser


class PlainHTMLParser(HTMLParser):
    '''
    HTMLParser implementation that strips HTML tags, preserving the content.
    This is not intended to interpret HTML, nor output sanitized and secure HTML
    that's safe to use in a web browser.

    This parses a string that may contain HTML, and removes HTML tags, and content
    that isn't intended for users to read, such as <script> and <style>. It will
    preserve the content of tags that is semantically intended to be read by the
    user, such <a>, <p>, and <span>.

    Implementation should always be locale independent. It works with the HTML,
    not string/ASCII content.
    '''
    html_elements = [
        "html", "base", "head", "link", "meta", "style", "title", "body",
        "address", "article", "aside", "footer", "header", "h1", "h2", "h3",
        "h4", "h5", "h6", "hgroup", "main", "nav", "section", "search",
        "blockquote", "dd", "div", "dl", "dt", "figcaption", "figure", "hr",
        "li", "menu", "ol", "p", "pre", "ul", "a", "abbr", "b", "bdi", "bdo",
        "br", "cite", "code", "data", "dfn", "em", "i", "kbd", "mark", "q",
        "rp", "rt", "ruby", "s", "samp", "small", "span", "strong", "sub",
        "sup", "time", "u", "var", "wbr", "area", "audio", "img", "map",
        "track", "video", "embed", "iframe", "object", "picture", "portal",
        "source", "svg", "math", "canvas", "noscript", "script", "del", "ins",
        "caption", "col", "colgroup", "table", "tbody", "td", "tfoot", "th",
        "thead", "tr", "button", "datalist", "fieldset", "form", "input",
        "label", "legend", "meter", "optgroup", "option", "output", "progress",
        "select", "textarea", "details", "dialog", "summary", "slot", "template"
    ]
    '''
    List of HTML elements, excluding obsolete and deprecated HTML elements.

    This allows us to seperate stylized text from actual HTML. For example,
    if a description or movie name contains "<3", it will be preserved because
    "3" is not the list of known HTML elements.

    See: https://developer.mozilla.org/en-US/docs/Web/HTML/Element
    '''

    inline_elements = [
        "a", "b", "em", "i", "s", "span", "strong", "sub", "sup", "u"
    ]
    '''
    List of inline HTML elements. Allows us know which element doesn't need to
    have whitespace appended.
    '''

    tag_denylist = [
        "head", "meta", "style", "canvas", "noscript", "script", "summary"
    ]
    '''
    Denylist of tags with content we don't want to display.

    We drop <summary> because it's part of the <details> tag, but since we'll
    always display the details anyway, there is no need for the summary of it.
    '''

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.elements = []
        self.accumulator = []
        self.pending_data = []
        self.result = None

    def handle_starttag(self, tag, _):
        if self.elements and self.elements[-1] in PlainHTMLParser.tag_denylist:
            return

        self.handle_pending_data()

        if tag not in PlainHTMLParser.html_elements:
            self.accumulator.append(self.get_starttag_text())
            return

        self.elements.append(tag)

    def handle_endtag(self, tag):
        self.handle_pending_data()

        if self.elements and self.elements[-1] == tag:
            self.elements.pop()
            return
        elif self.elements and self.elements[-1] in PlainHTMLParser.tag_denylist:
            return

        if tag not in PlainHTMLParser.html_elements:
            self.accumulator.append(self.get_starttag_text())

    def handle_startendtag(self, tag, _):
        if self.elements and self.elements[-1] in PlainHTMLParser.tag_denylist:
            return

        self.handle_pending_data()

        if tag not in PlainHTMLParser.html_elements:
            self.accumulator.append(self.get_starttag_text())

    def handle_data(self, data):
        if self.elements and self.elements[-1] in PlainHTMLParser.tag_denylist:
            return

        self.pending_data.append(data)

    def close(self):
        super().close()
        self.handle_pending_data()
        self.result = "".join(self.accumulator)

    def handle_pending_data(self):
        if not self.pending_data:
            return

        data_concat = "".join(self.pending_data)

        if self.accumulator and self.elements and self.elements[-1] not in PlainHTMLParser.inline_elements:
            data_concat = " " + data_concat

        self.accumulator.append(data_concat)
        self.pending_data.clear()
