// Steps:
// 1. Open convocation e-mail
// 2. Click the vertical dots button at the right of the e-mail.
// 3. Click "Afdrukken"
// 4. Cancel the print popup
// 5. Press F12 to open the developer console
// 6. Copy+paste this script into the console, and press Enter
// 7. Check no personal e-mail addresses are present anymore on the page.
// 8. You can now proceed to save the e-mail as a pdf.

// @[^"]+(>|,|$)

let messages = document.querySelectorAll("table.message");

for (let i = 1; i < messages.length; i++) {
  messages[i].remove();
}

let message = messages[0];

let bccContainer = message.querySelector(".recipient");
console.assert(bccContainer != null, "No BCC container found");

let text = bccContainer.innerText;
let findRegex = /bcc: (?<bccAddresses>.+)($|\n)/i;

let match = text.match(findRegex);
let bccAddressesCount = match.groups.bccAddresses.match(/@[^">,\n]+(>|,|$|\n)/g).length; 

let newText = text.replace(findRegex, `Bcc: [${bccAddressesCount} e-mail addresses]`);
bccContainer.innerText = newText;

let allText = document.body.innerText;
print(allText);

let isEmailAddressKillswitch = allText.includes("@hotmail.com");
print(isEmailAddressKillswitch);
console.assert(!isEmailAddressKillswitch, "Email address killswitch detected");

