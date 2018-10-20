from ..zptsupport import load_template

RENDERED = u"<html>\n<head>\n<title>%s</title>\n</head>\n\
<body>\n<div>Hello, %s</div>\n</body>\n</html>"


def test_template_lookup():
    template = load_template("loggerhead.tests.simple")
    assert template
    TITLE="test"
    NAME="World"
    info = dict(title=TITLE, name=NAME)
    s = template.expand(**info)
    assert s.startswith(RENDERED % (TITLE, NAME))
