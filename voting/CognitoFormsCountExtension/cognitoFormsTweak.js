let stopRepeatRequested = false;
// window.stopRepeatRequested = false;

function copyTest() {
    // https://stackoverflow.com/questions/69438702/why-does-navigator-clipboard-writetext-not-copy-text-to-clipboard-if-it-is-pro
    // answer by https://stackoverflow.com/users/7580839/amir-forsati
    return new Promise((resolve, reject) => {
        temp2.addEventListener("click", (e) => {
            const type = "text/html";
            const text = "<ol><li>Abcd</li><li>Def</li></ol>";
            const blob = new Blob([text], { type });
            const data = [new ClipboardItem({ [type]: blob })];
            navigator.permissions.query({name: "clipboard-write"}).then((permission) => {
                if (permission.state === "granted" || permission.state === "prompt") {
                    navigator.clipboard.write(data).then(resolve, reject).catch(reject);
                }
                else {
                    reject(new Error("Permission not granted!"));
                }
            });
        });
    }); 
}

function formatCounts(name, values) {
    let counts = {};

    for (let value of values) {
        if (!counts[value])
            counts[value] = 0;
        counts[value]++;
    }

    let countStr = Object.keys(counts).map((key) => `${key}: ${counts[key]}`).join("\n   ");
    return `<pre>${name}:\n   ${countStr}</pre>`;
}

function formatProposition(name, values) {
    let pro = values.filter((value) => value == "Pro").length;
    let against = values.filter((value) => value == "Against").length;
    let abstain = values.filter((value) => value == "Abstain").length;
    let total = values.length;

    let other = values.length - pro - against - abstain;
    let otherValues = values.filter((value) => value != "Pro" && value != "Against" && value != "Abstain");

    if (other > 0 || otherValues.length > 0) {
        // console.error(`Unexpected values for ${name}: ${otherValues.join(", ")}`);
        return formatCounts(name, values);
    }

    return (
     `<pre>${name}:\n` +
     `- The total number of votes cast was ${total}\n` +
     `- The number of abstensions was ${abstain}\n` +
     `- The remaining number of votes is therefore ${total - abstain}\n` +
     `- The final votes are as follows:\n` +
     `    * Pro: ${pro}\n` +
     `    * Against: ${against}\n</pre>`
    );
}

function updateValues() {
    let entriesMain = document.querySelector(".c-entries");
    let entriesEl = entriesMain?.querySelector("#c-entrylist");
            
    if (!entriesEl) {
        console.error("Entries element not found");
        return;
    }

    let headerColumnsDiv = entriesEl.querySelector(".slick-header-columns");
    if (!headerColumnsDiv) {
        console.error("Header columns div not found");
        return;
    }

    let headerColumns = headerColumnsDiv.querySelectorAll(".slick-header-column");

    let columnNames = Array.from(headerColumns).map((el) => el.querySelector(".slick-column-name")?.innerText ?? "");
    // console.log(`Column names: ${columnNames.join(", ")}`);

    let viewport = entriesEl.querySelector(".slick-viewport");
    let gridCanvas = viewport?.querySelector(".grid-canvas");
    let rowsEls = gridCanvas?.querySelectorAll(".slick-row");

    if (!rowsEls) {
        console.error("Rows not found");
        return;
    }

    let rows = Array.from(rowsEls).map((el) => {
        let cells = el.querySelectorAll(".slick-cell");
        return Array.from(cells).map((cell) => cell.innerText);
    });

    let entries = rows.map((row) => {
        console.assert (row.length == columnNames.length, `Row length ${row.length} does not match column names length ${columnNames.length}`);

        let entry = {};
        for (let i = 0; i < columnNames.length; i++) {
            entry[columnNames[i]] = row[i];
        }
        return entry;
    });

    let propositions = columnNames.slice(columnNames.indexOf("Submitted") + 1);
    let propositionsValues = {};
    
    for (let prop of propositions) {
        let propValues = entries.map((entry) => entry[prop]);
        propositionsValues[prop] = propValues;
    }

    let permittedValues = new Set(["Pro", "Against", "Abstain"]);

    console.log(propositionsValues);

    let validPropositions = propositions.filter((prop) => {
        let propValues = propositionsValues[prop];
        return propValues.every((value) => permittedValues.has(value));
    });

    let invalidPropositions = propositions.filter((prop) => {
        return !validPropositions.includes(prop);
    });

    // let message = `
    // Invalid propositions: ${invalidPropositions.join(", ")}
    // Column names: ${columnNames.join(", ")}\n    
    // Entries:\n${JSON.stringify(entries, null, 4)}`;

    // console.log(message);

    let entryDetails = document.querySelector("#c-entry-details .c-entry-details-info .panel__group");
    let toolbar = document.querySelector("#c-entry-details .entry-details-toolbar");

    if (!entryDetails) {
        console.error("Entry details not found");
        return;
    }

    let formattedResultsEl = entryDetails.querySelector(".formatted-results");
    if (!formattedResultsEl) {
        let entriesPanel = document.querySelector("#c-admin .c-entries");
        if (entriesPanel) {
            entriesPanel.setAttribute("data-show-entry-detail", "true");

            if (window.location.pathname.endsWith("/entries")) {
                for (let i = 0; i < 3 && i < entryDetails.children.length; i++) {
                    entryDetails.children[i].style.display = "none";
                }

                if (toolbar != null) {
                    toolbar.style.display = "none";
                }
            }
        }

        // formattedResultsEl = document.createElement("span");
        // formattedResultsEl.classList.add("formatted-results");
        // formattedResultsEl.classList.add("panel");

        let panel = document.createElement("template");

        let insertHTML = `
        <span class="panel"><span role="tab" aria-expanded="true" aria-controls="panel-content-4099" aria-describedby="panel-content-4099"><div id="panel-head-4099" role="button" tabindex="0" class="panel__header flex flex--sb print:hide is-expanded" style="top: 0px;">
        <h2 class="panel__title">Total votes</h2>
        <button class="panel__arrow is-expanded" style="display: none; transform: rotate(-6.52265deg);">
        <div class="panel__icon-plate"><i class="c-icon icon i-simple i-chevron-down"><svg viewBox="0 0 17 17" fill="none" class=""><path d="m14.5 5.5-6.026 6.026L2.447 5.5" stroke="#798f8f" stroke-width=".962" stroke-linecap="round" stroke-linejoin="round" class="i-stroke"></path></svg></i></div></button></div></span>
        <div id="panel-content-4099" role="tabpanel" aria-labelledby="panel-head-4099" class="panel__wrap"><div class="panel__content"><div></div> <div class="c-entry-details-embedded-form app-styled-form">
        <form lang="nl" tabindex="-1" class="cog-cognito cog-form cog-78 is-default cog-cognito--styled cog-form--light-background cog-form--show-all-pages cog-cognito--protect-css" data-width="700 650 625 600 575 550 525 500 475 450 425 400 375 350 325 300 275 250 225 200"><div class="cog-form__container">
        <div class="cog-form__content"><!----><div class="cog-body"><!----><div class="cog-page cog-wrapper cog-transition-ltr"><div class="cog-row">
        
        <fieldset class="cog-field cog-field--1 cog-col cog-col--24 cog-choice cog-choice--radiobuttons is-required">
            <legend class="cog-label">
			Expected number of votes<!----></legend>
            <div class="cog-input"><div class="el-input">
                <input type="text" autocomplete="off" placeholder="" class="el-input__inner" inputmode>
            </div></div> 
        </fieldset>
        <div class="formatted-results"></div>
        </div> <!----> <!----> <!----></div></div><!----><!----><!---->
        </div></div></form></div> <div></div></div></div></span>`;

        panel.innerHTML = insertHTML;
        entryDetails.appendChild(panel.content.cloneNode(true));

        formattedResultsEl = entryDetails.querySelector(".formatted-results");
    }

    // formattedResultsEl.innerHTML = `<pre>${message}</pre>`;
    formattedResultsEl.innerHTML = "";

    if (invalidPropositions.length > 0) {
        formattedResultsEl.innerHTML += `<pre>Invalid propositions: ${invalidPropositions.join(", ")}</pre>`;
    }
    for (let prop of validPropositions) {
        let propValues = propositionsValues[prop];
        let formattedProp = formatProposition(prop, propValues);
        formattedResultsEl.innerHTML += formattedProp;
    }

}

function doRepeatUpdate() {
    updateValues();

    // console.log(`stopRepeatRequested: ${window.stopRepeatRequested}`);

    if (!window.stopRepeatRequested)
        window.setTimeout(doRepeatUpdate, 5000);
}

function registerListeners() {
    console.log("Registering listeners");

    document.addEventListener("DOMContentLoaded", () => {
        try {
            console.log("Document loaded");

            doRepeatUpdate();

            // document.body.style.backgroundColor = "red";

            // window.setInterval(() => {
            //     if (numbersVisible)
            //         prependChannelNumbers();
            // }, 1500);

            // let style = `
            // .tv-guide-overlay {
            //     display: block;
            //     position: absolute;
            //     left: 0px;
            //     top: 0px;
            //     right: 0px;
            //     bottom: 0px;
            //     padding: 80px;
            //     background-color: hsla(306, 59%, 68%, 60%);
            //     z-index: 10;
            // }

            // .tv-guide-overlay.hidden {
            //     visibility: hidden;
            //     content-visibility: hidden;
            //     z-index = -10;
            // }
            // `;

            // let styleEl = document.createElement("style");
            // styleEl.innerHTML = style;
            // document.head.appendChild(styleEl);

            // window.setTimeout(() => {
            //     try {
            //         // document.addEventListener("keydown", (e) => {

            //         // }, true);
            //         prependChannelNumbers();

            //         // window.setTimeout(() => {
            //         //     prependChannelNumbers();
            //         // }, 2000);

            //         console.log("Enabled remote control tweaks.");
            //     } catch (e) {
            //         console.log(`Error in attaching to player: ${e}`)
            //     }
            // }, 1000);

            // window.setTimeout(() => {
            //     if (window.location.href == "https://www.ziggogo.tv/nl.html")
            //         addZiggoTVGidsOverlay();
            // }, 3000);
        } catch (e) {
            console.log(`Error remote control tweaks: ${e}`);
        }
    });

}


try {
    console.log(`Href is ${window.location.href}`);

    const urlParams = new URLSearchParams(window.location.search);
    // let overlay = urlParams.get("overlay");
    // console.log("Overlay:");
    // console.log(overlay);

    if (window.location.href.match(
        /^https?:\/\/([a-z0-9]+\.)?cognitoforms.com\//.source +
        /([a-z0-9_-]{1,30}\/){0,4}.*[/_-]entries(?![a-z])(\/[0-9]+)?\/?$/.source
    )
        //  && overlay
    ) {
        registerListeners();
    }
} catch (e) {
    console.error(`Error setting up Ziggo TV gids tweaks: ${e}`);
}
