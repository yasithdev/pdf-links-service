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

function robustify(pdf_hash, target) {
  // declare element variables
  const logEl = document.getElementById("log");
  const progressEl = document.getElementById("progress");
  const spinnerEl = document.getElementById("spinner");
  const selectorEl = document.getElementById("all");
  const urlsEl = [...document.getElementsByName('url').values()];
  // initialize state variables / functions
  const decoder = new TextDecoder('utf-8');
  // get selected items
  const urls = urlsEl.filter(e => e.checked).map(e => e.value);
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
  [...urlsEl, target, selectorEl].forEach(e => e.toggleAttribute("disabled", true));
  updateProgress();
  // call the robustify API
  fetch("/robustify", {
    method: "post",
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({pdf_hash: pdf_hash, uris: urls})
  })
    .then(response => response.body.getReader())
    .then(async reader => {
      while (true) {
        let buffer = "";
        const {done, value} = await reader.read();
        if (done) break;
        // append to buffer
        buffer += decoder.decode(value);
        while (true) {
          const breakpoint = buffer.indexOf("\n");
          if (breakpoint === -1) break;
          const chunk = buffer.slice(0, breakpoint);
          buffer = buffer.slice(breakpoint + 1);
          // skip if chunk is invalid
          if (chunk.length <= 2 || chunk[0] !== '{' || chunk[chunk.length - 1] !== '}') continue;
          // incremental update
          const res = JSON.parse(chunk);
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
      }
    })
    .catch(err => {
      console.log("Error from API", err);
    })
    .finally(_ => {
      // final update
      [...urlsEl, target, selectorEl].forEach(e => e.toggleAttribute("disabled", false));
      spinnerEl.classList.toggle("d-none", true);
      updateProgress();
    })
}

function getLDN(pdf_hash, element_id) {
  const ld_server_url = document.getElementById(element_id).value;
  return fetch(`/ldn/${pdf_hash}?ld_server_url=${ld_server_url}`, {headers: {'Accept': 'application/json'}})
    .then(async res => await res.json())
    .then(json => JSON.stringify(json, null, 2));
}

function previewLDN(ldn) {
  return fetch(`/preview`, {
    method: "post",
    headers: {'Content-Type': 'application/json'},
    body: ldn,
  }).then(res => window.open(res.url, "_blank"));
}

function sendLDN(pdf_hash, element_id) {
  const ld_server_url = document.getElementById(element_id).value;
  return fetch(`/ldn/${pdf_hash}`, {
    method: "post",
    headers: {'Content-Type': 'application/json', 'Accept': 'application/json'},
    body: JSON.stringify({ld_server_url: ld_server_url})
  }).then(res => {
    if (!res.ok) {
      return Promise.reject(res.status);
    } else {
      return res.status;
    }
  })
}