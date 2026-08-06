/* Odometer hero — the app's headline action, on the page.
 *
 * Garage Buddy's first move is photographing an odometer and reading the
 * number off it, so the landing page opens with an odometer settling on a
 * reading rather than with a paragraph.
 *
 * Digits roll independently, right to left, the way a mechanical drum does:
 * the ones place spins longest, the ten-thousands barely moves. Reduced
 * motion gets the final reading immediately.
 */
(function () {
  "use strict";

  var FINAL = "087421";       // illustrative reading, not real data
  var ROLL_MS = 1500;         // total settle time for the fastest drum

  function mount(host) {
    var digits = [];
    var row = document.createElement("div");
    row.className = "odo-row";

    for (var i = 0; i < FINAL.length; i++) {
      var cell = document.createElement("span");
      cell.className = "odo-digit" + (i === FINAL.length - 1 ? " odo-tenth" : "");
      cell.textContent = "0";
      row.appendChild(cell);
      digits.push(cell);
    }

    host.appendChild(row);
    host.setAttribute("role", "img");
    host.setAttribute("aria-label",
      "An odometer reading " + Number(FINAL).toLocaleString() + " miles");

    function settle() {
      for (var i = 0; i < digits.length; i++) {
        digits[i].textContent = FINAL[i];
      }
    }

    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
      settle();
      return;
    }

    var start = null;
    (function frame(now) {
      if (start === null) start = now;
      var t = (now - start);
      var running = false;

      for (var i = 0; i < digits.length; i++) {
        // Place 0 is the leftmost (slowest); the rightmost spins longest.
        var place = digits.length - 1 - i;
        var dur = ROLL_MS * Math.pow(0.62, place);
        if (t >= dur) {
          digits[i].textContent = FINAL[i];
        } else {
          running = true;
          digits[i].textContent = String(Math.floor(Math.random() * 10));
        }
      }
      if (running) requestAnimationFrame(frame);
      else settle();
    })(performance.now());
  }

  function init() {
    var host = document.querySelector("[data-odometer]");
    if (host) mount(host);
  }
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
