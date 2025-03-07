
function crossOrigResolve_beforeSend(details) {
    // console.log("OnBeforeSendHeaders triggered");
    // console.log("Input headers:");
    console.log(details.requestHeaders);
    requestHeaders = details.requestHeaders.filter(
        (value) => {
            return !value.name.startsWith("Sec-Fetch-");
        }
    );

    // console.log("Output headers:");
    // console.log(requestHeaders);

    return {
        requestHeaders: requestHeaders
    };
}

function crossOrigResolve_received(details) {
    console.log("headersReceived triggered");
    try {
        console.error(`Url is ${details.documentUrl || details.url}`);

        if (!(details.documentUrl || details.url).match(/^https:\/\/(\w+\.)?ziggogo.tv\/.*$/)) {
            //console.warn(`Not resolving received headers, ancestor url was ${details.frameAncestors[0].url}`);
            return {
                responseHeaders: details.responseHeaders
            };
        }
        //console.log("Resolving received headers");

        let removeHeaders = ["Content-Security-Policy", "X-Frame-Options"];

        let responseHeaders = details.responseHeaders.filter(
            (value) => {
                return !removeHeaders.includes(value.name);
            }
        );

        return {
            responseHeaders: responseHeaders
        }

    } catch (e) {
        console.error(`Error solving received headers: ${e}`);
    }
}

try {
    let br = null;
    if (typeof browser !== "undefined")
        br = browser;
    else
        br = chrome;

    // // BEGIN Based on https://stackoverflow.com/questions/3274144/can-i-modify-outgoing-request-headers-with-a-chrome-extension
    // br.webRequest.onBeforeSendHeaders.addListener(
    //     crossOrigResolve_beforeSend,
    //     { urls: ["https://www.ziggogo.tv/nl/tv/tv-kijken.html"] },
    //     ["blocking", "requestHeaders"]
    // )
    // // END Based on

    // br.webRequest.onHeadersReceived.addListener(
    //     crossOrigResolve_received,
    //     { urls: ["https://*.ziggogo.tv/*"] },
    //     ["blocking", "responseHeaders"]
    // )


    console.log("Added TV guide cross origin resolve listeners");
} catch (e) {
    console.error(`Error adding onBeforeSendHeaders listener: ${e}`);
}

