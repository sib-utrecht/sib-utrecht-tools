# This was an experimental script whose development has been suspended.

def process_deregistration_email(dkim_result: DKIMDetailsVerified):
    html_content, text_content = (
        get_html_and_plain_from_mail_message(dkim_result.email)
    )

    forwardedHeader = re.compile(
        r"""[.\n]{0,300}\n"""
        r"""---------- Forwarded message ---------\n"""
        r"""Van: [^<\n]*<(?P<sender>[^>\n]+)>\n"""
        r"""Date: (?P<date>[^<\n]+)\n"""
    )
    # Date can be for example 'za 2 aug 2025 om 16:52'

    # text_content = dkim_result.email.get_content("text/plain")
    with open("debug.txt", "w") as f:
        f.write("Content of mail:")
        f.write(text_content)

    match = forwardedHeader.search(text_content.replace("\r\n", "\n"))

    if not match:
        logger.error("No forwarded header found in deregistration email")
        return False
    
    sender = match.group("sender")
    date_str = match.group("date").strip()

    print(f"Sender: {sender}")
    print(f"Date: {date_str}")

    # Parse the date
    try:
        with setlocale(locale.LC_TIME, "nl_NL.UTF-8"):
            # Assuming the date format is 'za 2 aug 2025 om 16:52'
            date = datetime.strptime(date_str, "%a %d %b %Y om %H:%M")
    except ValueError as e:
        logger.error(f"Failed to parse date '{date_str}': {e}")
        return False

    logger.info(f"Parsed date: {date.isoformat()}")


    fields = extract_fields_from_mail_message(dkim_result.email)

    canonical = form_to_canonical(fields)
    logger.info(f"Canonical form: {json.dumps(canonical, indent=2)}")

    # Extract the member ID from the canonical form
    member_id = canonical.get("member_id", None)
    if not member_id:
        logger.error("No member ID found in deregistration email")
        return False

    # Here you would implement the logic to remove the member from Conscribo
    # For now, we just log it
    logger.info(f"Deregistering member with ID: {member_id}")
