def increase_indent(text, num_spaces=2):
    """Increase indentation of the given text by num_spaces spaces."""
    lines = text.splitlines()
    indented_lines = [" " * num_spaces + line for line in lines]
    return "\n".join(indented_lines)