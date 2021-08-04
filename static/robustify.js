function showToast(elementId) {
  new bootstrap.Toast(document.getElementById(elementId)).show()
}

function copyToClipboard(textToCopy) {
  // source: https://stackoverflow.com/questions/51805395/navigator-clipboard-is-undefined
  // navigator clipboard api needs a secure context (https)
  if (navigator.clipboard && window.isSecureContext) {
    // navigator clipboard api method'
    return navigator.clipboard.writeText(textToCopy).then(_ => showToast('copiedToast'));
  } else {
    // text area method
    let textArea = document.createElement("textarea");
    textArea.value = textToCopy;
    // make the textarea out of viewport
    textArea.style.position = "fixed";
    textArea.style.left = "-999999px";
    textArea.style.top = "-999999px";
    document.body.appendChild(textArea);
    textArea.focus();
    textArea.select();
    return new Promise((res, rej) => {
      // here the magic happens
      document.execCommand('copy') ? res() : rej();
      textArea.remove();
    }).then(_ => showToast('copiedToast'));
  }
}

function bs_card_done(uri, href_uri_r, cp_href_uri_r, href_uri_m, cp_href_uri_m) {
  return String.raw`
<div class="card mb-1">
  <div class="card-header px-2 bg-success text-white">
    <b class="nowrap">${uri}</b>
  </div>
  <div class="card-body p-2">
    <table class="card-text w-100">
    <tbody>
      <tr>
        <td class="w-4em"><b>URI-R:</b></td>
        <td>${href_uri_r}</td>
        <td class="w-4em">
          <button
            type="button"
            class="btn btn-success btn-sm float-end text-xs"
            onclick='copyToClipboard(${cp_href_uri_r})'>Copy</button></td>
      </tr>
      <tr>
        <td class="w-4em"><b>URI-M:</b></td>
        <td>${href_uri_m}</td>
        <td class="w-4em">
        <button
          type="button"
          class="btn btn-success btn-sm float-end text-xs"
          onclick='copyToClipboard(${cp_href_uri_m})'>Copy</button></td>
      </tr>
    </tbody>
    </table>
  </div>
</div>`;
}

function bs_card_fail(uri, err) {
  return String.raw`
<div class="card mb-1">
  <div class="card-header px-2 bg-warning text-white">
    <b>${uri}</b>
  </div>
  <div class="card-body p-2">
    <table class="card-text w-100">
    <tbody>
      <tr>
        <td class="w-4em"><b>Error:</b></td>
        <td>${err}</td>
      </tr>
    </tbody>
    </table>
  </div>
</div>`;
}

function robustify(filename, target) {
  // declare element variables
  const logEl = document.getElementById("log");
  const progressEl = document.getElementById("progress");
  const spinnerEl = document.getElementById("spinner");
  // initialize state variables / functions
  const decoder = new TextDecoder('utf-8');
  // get selected items
  const items = [...document.getElementsByName('url').values()];
  const urls = items.filter(e => e.checked).map(e => e.value);
  if (urls.length === 0) {
    alert('Please select at least one URL first.');
    return;
  }
  const passUrls = [];
  const failUrls = [];
  const updateProgress = () => progressEl.innerHTML = `Pass: ${passUrls.length}, Fail: ${failUrls.length}, Total: ${urls.length}`;
  // initialize UI
  logEl.innerHTML = "";
  spinnerEl.classList.toggle("d-none", false);
  items.forEach(e => e.toggleAttribute("disabled", true));
  target.toggleAttribute("disabled", true);
  updateProgress();
  // call the robustify API
  fetch("/robustify", {
    method: "post",
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({filename: filename, uris: urls})
  })
    .then(response => response.body.getReader())
    .then(async reader => {
      while (true) {
        const {done, value} = await reader.read();
        if (done) {
          // final update
          items.forEach(e => e.toggleAttribute("disabled", false));
          target.toggleAttribute("disabled", false);
          spinnerEl.classList.toggle("d-none", true);
          updateProgress();
          break;
        }
        // incremental update
        const res = JSON.parse(decoder.decode(value).trim());
        const uri = res['uri'];
        if (res['ok']) {
          const href_uri_r = res['href_uri_r'].replaceAll(/[\s\n]+/g, " ");
          const cp_href_uri_r = "`" + href_uri_r.replaceAll("'", '"') + "`";
          const href_uri_m = res['href_uri_m'].replaceAll(/[\s\n]+/g, " ");
          const cp_href_uri_m = "`" + href_uri_m.replaceAll("'", '"') + "`";
          logEl.innerHTML += bs_card_done(uri, href_uri_r, cp_href_uri_r, href_uri_m, cp_href_uri_m);
          passUrls.push(uri);
        } else {
          const err = res['error'];
          logEl.innerHTML += bs_card_fail(uri, err);
          failUrls.push(uri);
        }
        updateProgress();
      }
    })
}

function getLDN(filename) {
  return fetch(`/ldn/${filename}`)
    .then(async res => await res.json())
    .then(json => JSON.stringify(json, null, 2));
}

function sendLDN(filename, addr) {
  return fetch(`/ldn/${filename}`, {
    method: "post",
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({to: addr})
  }).then(res => res.status)
}