import requests
import json
import regex
import urllib
from urllib.parse import urlparse, urlencode

# url = "https://docs.google.com/spreadsheets/d/1l-DQhGXPq3QlMPor1aZk2Cw_VpxaHUZWDPFnt9Cd0Hg/edit?usp=sharing"

# Url as in browser
url = "https://docs.google.com/spreadsheets/d/1l-DQhGXPq3QlMPor1aZk2Cw_VpxaHUZWDPFnt9Cd0Hg/edit?gid=0#gid=0"

id_regex = regex.Regex(r"/d/(?P<spreadsheet_id>[a-zA-Z0-9-_]{10,})/")
spreatsheet_id = id_regex.search(url).group("spreadsheet_id")

# tsv_url = url.replace("/edit", "/gviz/tq?tqx=out:tsv&sheet=Sheet1")

tsv_url_object = urlparse(url)
tsv_url_object = tsv_url_object._replace(
    path=tsv_url_object.path.replace("/edit", "/export"),
    query=tsv_url_object.query + f"&format=tsv&id={spreatsheet_id}"
)
tsv_url = tsv_url_object.geturl()

# tsv_url = url.replace("/edit", f"/export")
# parsed = urlparse(tsv_url)
# parsed = parsed._replace()
# print(f"Parsed URL: {parsed}")
# tsv_url = parsed.geturl()

print(f"TSV URL: {tsv_url}")

# parsed = 

# url = urllib.parse.quote(url, safe=":/?&=")



def get_tsv_data(url):
    """
    Fetches the TSV data from the given URL.
    """
    response = requests.get(url)
    print(f"Status code: {response.status_code}")
    print(f"Response text: {response.text[:100]}...")  # Print first 100 characters of the response

    if response.status_code == 200:
        return response.text
    else:
        raise Exception(f"Failed to fetch data: {response.status_code}")
    
# def make_homogeneous(data):
#     row_length = len(data[0])

#     return [
#         [
#             row[i] if i < len(row) else ""
#             for i in range(row_length)
#         ]
#         for row in data
#     ]

def parse_tsv_data(tsv_data : str):
    """
    Parses the TSV data and returns a list of dictionaries.
    """
    lines = tsv_data.strip().split("\n")
    headers = lines[0].strip().split("\t")
    data = []
    
    for line in lines[1:]:
        values = line.strip().split("\t")
        values = [
            values[i].strip()
            if i < len(values) else ""
            for i in range(len(headers))
        ]

        entry = {headers[i]: values[i] for i in range(len(headers))}
        data.append(entry)
    
    return data

def fetch_and_parse_tsv_data():
    """
    Main function to fetch and parse the TSV data.
    """
    tsv_data = get_tsv_data(tsv_url)
    parsed_data = parse_tsv_data(tsv_data)
    return parsed_data

_parsed_data = None

def get_parsed_data():
    global _parsed_data

    if _parsed_data is not None:
        return _parsed_data

    _parsed_data = fetch_and_parse_tsv_data()
    return _parsed_data
    
def get_register_form_to_key() -> dict:
    parsed_data = get_parsed_data()
    
    register_form_to_key = {
        row["RegisterForm"]: row["Key"]

        for row in parsed_data
        if row.get("RegisterForm") and row.get("Key")
    }

    return register_form_to_key

def get_conscribo_to_key() -> dict:
    parsed_data = get_parsed_data()

    conscribo_to_key = {
        row["Conscribo"]: row["Key"]

        for row in parsed_data
        if row.get("Conscribo") and row.get("Key")
    }

    return conscribo_to_key




def main():
    parsed_data = get_parsed_data()    

    print("\n\n\nPrinting data")
    
    # Print the parsed data
    for entry in parsed_data:
        print(json.dumps(entry, indent=4))


    print("\n\n\nPrinting register_form_to_key")
    print(json.dumps(get_register_form_to_key(), indent=4))
    print("\n\n\nPrinting conscribo_to_key")
    print(json.dumps(get_conscribo_to_key(), indent=4))



if __name__ == "__main__":
    main()