import logging


def increase_indent(text, num_spaces=2):
    """Increase indentation of the given text by num_spaces spaces."""
    lines = text.splitlines()
    indented_lines = [" " * num_spaces + line for line in lines]
    return "\n".join(indented_lines)


def print_header(line: str, logger: logging.Logger):
    """Log a standardized light-blue header with matching underline and spacing.

    - Blank line before and after
    - Title and underline in ANSI light blue (94)
    - Underline length matches the title
    """
    if logger is None:
        logger = logging.getLogger(__name__)

    logger.info("")
    underline = "=" * len(line)
    logger.info(f"\x1b[94m{line}\x1b[0m")
    logger.info(f"\x1b[94m{underline}\x1b[0m")
    logger.info("")

def print_change_count(count : int, logger: logging.Logger):
    """Log the count of changes in a standardized format."""
    if logger is None:
        logger = logging.getLogger(__name__)

    logger.info("")
    if count == 0:
        logger.info("\x1b[32mAlready up to date! No changes made.\x1b[0m")
    else:
        logger.info(f"\x1b[33m{count} changes made.\x1b[0m")
