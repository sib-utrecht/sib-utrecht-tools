vkuhlmann: Consider the JavaScript code
````
function formatHuisnummer(nummer, toevoeging, huisletter, huis_nlt) {
    if (toevoeging != null) {
        let match = toevoeging.match(/^(BS)?([A-Z]?)$/);

        if (match == null) {
            return huis_nlt;
        }

        let val = `${nummer}`;
        if (match[1] != null) {
            val += " bis";
        }

        if (match[2] != null && match[2].length > 0) {
            val += ` ${match[2]}`;
        }
        return val;
    }

    return huis_nlt;    
}

async function getForPostalCode(postcode) {
    postcode = postcode.replaceAll(" ", "");
    let docs = [];

    if (postcode.length == 6) {
        let fetchResponse = await fetch(`https://api.pdok.nl/bzk/locatieserver/search/v3_1/free?q=${postcode}&rows=100&df=postcode`);
        // Using code from https://developer.mozilla.org/en-US/docs/Web/API/Fetch_API/Using_Fetch
        if (!fetchResponse.ok) {
            throw new Error(`Response status: ${fetchResponse.status}`);
        }

        const data = await fetchResponse.json();

        docs = Array.from(data.response.docs);
    }

    let postcode_infos = docs.filter((v, _) => v.type == "postcode");
    let plaatsnamen = [...new Set(postcode_infos.map((v) => v.woonplaatsnaam))].sort();
    let straatnamen = [...new Set(postcode_infos.map((v) => v.straatnaam))].sort();

    let addresses = docs.filter((v, _) => v.type == "adres");

    addresses = addresses.map((v, _) => {
        return {
            "nummer": formatHuisnummer(
                v['huisnummer'],
                v['huisnummertoevoeging'],
                v['huisletter'],
                v['huis_nlt']
            ),
            "huis_nlt": v["huis_nlt"],
            "plaatsnaam": v.woonplaatsnaam,
            "straatnaam": v.straatnaam,
            "rdf": v["rdf_seealso"],
            "details": v
        };
    });

    return {
        "plaatsnamen": plaatsnamen,
        "straatnamen": straatnamen,
        "adressen": addresses,
        "postalCode": postcode
    };
}
```

Implement this in check_basic.py, in the get_for_postalcode stub, and  format_house_number. Note the JavaScript file uses Dutch naming, replace them with their English translations. 

GitHub Copilot: I'll help you implement the JavaScript functions in Python. First, let me read the current `check_basic.py` file to understand the existing structure and locate the stubs. Let me continue reading the file to see the rest of the implementation: Now I'll check if there are any existing imports at the top of the file to understand what libraries are already being used: Perfect! Now I'll implement the two functions based on the JavaScript code. I need to add the necessary imports and implement both `format_house_number` and `get_for_postal_code` functions. Let me start by adding the required imports: 
```


Made changes.


```
I need to check if aiohttp is installed or if I should use requests instead. Let me check what packages are available: Great! I see that `requests` is already a dependency. I'll use `requests` instead of `aiohttp` for the HTTP calls. Let me update the imports: 
```


Made changes.


```
Now let me implement the `format_house_number` function. Looking at the JavaScript code, I need to translate the Dutch parameter names to English: 
```


Made changes.


```
Now let me implement the `get_for_postal_code` function. I need to update the `AddressOuput` class first to match the return structure from the JavaScript: 
```


Made changes.


```
Now let me implement the `get_for_postal_code` function: 
```


Made changes.


```
Now let me check if there are any errors in the implementation: Great! The implementation looks good. Let me also check if the existing code in the `check_address` function needs to be updated to work with the new `AddressOuput` structure. Let me read that section: Let me read the `check_address` function to see how it uses `get_for_postal_code`: Perfect! The implementation looks complete and correct. Let me provide a summary of what I've implemented:

## Summary

I've successfully implemented the two functions in Python based on the JavaScript code:

### 1. `format_house_number` function
- **Purpose**: Formats Dutch house numbers with additions and letters
- **Translation**: 
  - `nummer` → `number`
  - `toevoeging` → `addition` 
  - `huisletter` → `house_letter`
  - `huis_nlt` → `house_number`
- **Logic**: 
  - Uses regex to parse additions in format `(BS)?([A-Z]?)`
  - Adds "bis" for "BS" prefix
  - Adds letter suffix if present
  - Returns formatted string or fallback value

### 2. `get_for_postal_code` function
- **Purpose**: Fetches address data from Dutch PDOK API for a given postal code
- **Translation**:
  - `postcode` → `postal_code`
  - `plaatsnamen` → `place_names`
  - `straatnamen` → `street_names`
  - `adressen` → `addresses`
  - `woonplaatsnaam` → `place_name`
  - `straatnaam` → `street_name`
- **Logic**:
  - Removes spaces from postal code
  - Fetches data from PDOK API if postal code is 6 characters
  - Filters results by type ("postcode" and "adres")
  - Formats addresses using the `format_house_number` function
  - Returns `AddressOuput` dataclass with all the structured data

### Key Changes Made:
1. **Added imports**: `re` and `requests` for regex and HTTP functionality
2. **Implemented error handling**: Using try-catch for API requests
3. **Used existing dependencies**: Leveraged `requests` instead of `aiohttp`
4. **Maintained compatibility**: The functions work with the existing `check_address` function
5. **Added comprehensive documentation**: Both functions have detailed docstrings

The implementation follows Python best practices and integrates seamlessly with the existing codebase structure.