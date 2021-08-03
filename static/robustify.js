function copyToClipboard(textToCopy) {
  // source: https://stackoverflow.com/questions/51805395/navigator-clipboard-is-undefined
  const showToast = () => new bootstrap.Toast(document.getElementById("copiedToast")).show();
  // navigator clipboard api needs a secure context (https)
  if (navigator.clipboard && window.isSecureContext) {
    // navigator clipboard api method'
    return navigator.clipboard.writeText(textToCopy).then(showToast);
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
    }).then(showToast);
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
  const urlEls = [...document.getElementsByName("url").values()];
  // initialize state variables / functions
  const decoder = new TextDecoder('utf-8');
  const urls = JSON.parse(target.dataset.urls);
  const passUrls = [];
  const failUrls = [];
  const updateProgress = () => progressEl.innerHTML = `Pass: ${passUrls.length}, Fail: ${failUrls.length}, Total: ${urls.length}`;
  // initialize UI
  logEl.innerHTML = "";
  urlEls.forEach(e => e.setAttribute("disabled", ""));
  spinnerEl.classList.toggle("d-none", false);
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
          urlEls.forEach(e => e.removeAttribute("disabled"));
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
        // button colors
        urlEls.filter(e => JSON.parse(e.dataset.urls).every(u => passUrls.includes(u)))
          .forEach(e => e.classList.replace("btn-primary", "btn-success"));
        urlEls.filter(e => JSON.parse(e.dataset.urls).some(u => failUrls.includes(u)))
          .forEach(e => {
            e.classList.replace("btn-primary", "btn-warning");
            e.classList.replace("btn-success", "btn-warning");
          });
      }
    })
}

function getLDN(filename) {
  return fetch(`/ldn/${filename}`)
    .then(async res => await res.json())
    .then(json => JSON.stringify(json, null, 2));
}