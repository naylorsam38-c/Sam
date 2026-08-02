/* ==========================================================================
   Chew Cartel — site behaviour
   Cart state lives in localStorage so the whole site works from static
   hosting with no backend. Swap the checkout handler for a real payment
   provider when the store goes live.
   ========================================================================== */

const CART_KEY = "chewcartel.cart.v1";
const FREE_SHIPPING_THRESHOLD = 49;
const FLAT_SHIPPING = 6.95;

/* ---------------------------------------------------------------- helpers */

function money(n) {
  return "$" + n.toFixed(2);
}

function stars(rating) {
  const full = Math.round(rating);
  return "★".repeat(full) + "☆".repeat(5 - full);
}

/* Placeholder pack mark, used until real product photography is dropped in. */
function packMark() {
  return `
    <svg viewBox="0 0 120 120" aria-hidden="true">
      <rect x="26" y="22" width="68" height="82" rx="6" fill="#14110f"/>
      <path d="M26 22h68v12H26z" fill="#4a3728"/>
      <circle cx="60" cy="64" r="22" fill="none" stroke="#c08a3e" stroke-width="2"/>
      <g fill="#c08a3e">
        <path d="M49 52 L57 59 L52 69 Z"/>
        <path d="M71 52 L63 59 L68 69 Z"/>
        <ellipse cx="60" cy="66" rx="11" ry="10"/>
        <ellipse cx="60" cy="74" rx="6.5" ry="5.5"/>
      </g>
      <g fill="#14110f">
        <circle cx="56" cy="64" r="1.5"/>
        <circle cx="64" cy="64" r="1.5"/>
        <ellipse cx="60" cy="71" rx="2.5" ry="2"/>
      </g>
    </svg>`;
}

function productMedia(p) {
  return p.image
    ? `<img src="${p.image}" alt="${p.name}" loading="lazy">`
    : packMark();
}

/* ------------------------------------------------------------------ toast */

let toastTimer;
function toast(message) {
  let el = document.querySelector(".toast");
  if (!el) {
    el = document.createElement("div");
    el.className = "toast";
    el.setAttribute("role", "status");
    document.body.appendChild(el);
  }
  el.textContent = message;
  requestAnimationFrame(() => el.classList.add("is-visible"));
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => el.classList.remove("is-visible"), 2600);
}

/* ------------------------------------------------------------------- cart */

function loadCart() {
  try {
    const raw = localStorage.getItem(CART_KEY);
    return raw ? JSON.parse(raw) : [];
  } catch {
    return [];
  }
}

function saveCart(cart) {
  try {
    localStorage.setItem(CART_KEY, JSON.stringify(cart));
  } catch {
    /* storage unavailable — cart just won't persist */
  }
  paintCartCount();
}

function addToCart(id, mode = "once", qty = 1) {
  const cart = loadCart();
  const line = cart.find((l) => l.id === id && l.mode === mode);
  if (line) {
    line.qty += qty;
  } else {
    cart.push({ id, mode, qty });
  }
  saveCart(cart);
  const p = getProduct(id);
  toast(`${p ? p.name : "Item"} added to bag`);
}

function cartCount() {
  return loadCart().reduce((n, l) => n + l.qty, 0);
}

function cartSubtotal() {
  return loadCart().reduce((sum, line) => {
    const p = getProduct(line.id);
    if (!p) return sum;
    const unit = line.mode === "sub" ? subscriptionPrice(p.price) : p.price;
    return sum + unit * line.qty;
  }, 0);
}

function paintCartCount() {
  const n = cartCount();
  document.querySelectorAll("[data-cart-count]").forEach((el) => {
    el.textContent = n;
    el.hidden = n === 0;
  });
}

/* -------------------------------------------------------------- rendering */

function productCard(p) {
  const flagClass = p.badgeStyle === "tan" ? "card-flag card-flag--tan" : "card-flag";
  const flag = p.badge ? `<span class="${flagClass}">${p.badge}</span>` : "";
  return `
    <article class="card">
      <a class="card-media" href="product.html?id=${p.id}" aria-label="${p.name}">
        ${flag}
        ${productMedia(p)}
      </a>
      <div class="card-body">
        <div class="stars" aria-label="Rated ${p.rating} out of 5">
          ${stars(p.rating)}<span>(${p.reviews})</span>
        </div>
        <h3><a href="product.html?id=${p.id}">${p.name}</a></h3>
        <p class="card-benefit">${p.tagline}</p>
        <div class="card-foot">
          <div class="price">
            ${money(p.price)}
            <small>${money(subscriptionPrice(p.price))} on subscription</small>
          </div>
          <button class="btn btn--sm" data-add="${p.id}">Add</button>
        </div>
      </div>
    </article>`;
}

function renderGrid(target, list) {
  const el = typeof target === "string" ? document.querySelector(target) : target;
  if (!el) return;
  el.innerHTML = list.map(productCard).join("");
}

/* ------------------------------------------------------------------ pages */

function initHome() {
  const grid = document.querySelector("[data-featured]");
  if (!grid) return;
  const picks = PRODUCTS.filter((p) => p.badge === "Best seller" || p.id === "chicken-training-bites" || p.id === "hip-joint-chews");
  renderGrid(grid, picks.slice(0, 4));
}

function initShop() {
  const grid = document.querySelector("[data-shop-grid]");
  if (!grid) return;

  const filterBar = document.querySelector("[data-filters]");
  const countEl = document.querySelector("[data-result-count]");

  function apply(cat) {
    const list = cat === "all" ? PRODUCTS : PRODUCTS.filter((p) => p.category === cat);
    renderGrid(grid, list);
    if (countEl) {
      countEl.textContent = `${list.length} ${list.length === 1 ? "product" : "products"}`;
    }
  }

  if (filterBar) {
    filterBar.innerHTML = CATEGORIES.map(
      (c) =>
        `<button class="chip" data-cat="${c.id}" aria-pressed="${c.id === "all"}">${c.label}</button>`
    ).join("");

    filterBar.addEventListener("click", (e) => {
      const btn = e.target.closest("[data-cat]");
      if (!btn) return;
      filterBar.querySelectorAll(".chip").forEach((c) => c.setAttribute("aria-pressed", "false"));
      btn.setAttribute("aria-pressed", "true");
      apply(btn.dataset.cat);
    });
  }

  const initial = new URLSearchParams(location.search).get("cat") || "all";
  const preset = filterBar && filterBar.querySelector(`[data-cat="${initial}"]`);
  if (preset) {
    filterBar.querySelectorAll(".chip").forEach((c) => c.setAttribute("aria-pressed", "false"));
    preset.setAttribute("aria-pressed", "true");
  }
  apply(initial);
}

function initProduct() {
  const root = document.querySelector("[data-pdp]");
  if (!root) return;

  const id = new URLSearchParams(location.search).get("id");
  const p = getProduct(id) || PRODUCTS[0];

  document.title = `${p.name} — Chew Cartel`;

  const crumb = document.querySelector("[data-pdp-crumb]");
  if (crumb) crumb.textContent = p.name;

  root.innerHTML = `
    <div class="figure">${productMedia(p)}</div>
    <div>
      <div class="stars" aria-label="Rated ${p.rating} out of 5">
        ${stars(p.rating)}<span>(${p.reviews} reviews)</span>
      </div>
      <h1>${p.name}</h1>
      <p class="lede">${p.tagline}</p>

      <ul class="tick-list" style="margin-bottom:2rem">
        ${p.benefits
          .map(
            (b) => `<li>
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" aria-hidden="true"><path d="M20 6 9 17l-5-5"/></svg>
              <span>${b}</span>
            </li>`
          )
          .join("")}
      </ul>

      <div style="display:grid;gap:0.75rem;margin-bottom:1.5rem">
        <label class="buy-option">
          <input type="radio" name="buymode" value="sub" checked>
          <span style="flex:1">
            <strong>Subscribe &amp; save</strong>
            <span>Delivered every 4 weeks. Skip, change or cancel any time.</span>
          </span>
          <span class="opt-price">${money(subscriptionPrice(p.price))}</span>
        </label>
        <label class="buy-option">
          <input type="radio" name="buymode" value="once">
          <span style="flex:1">
            <strong>One time</strong>
            <span>Just the once, no commitment.</span>
          </span>
          <span class="opt-price">${money(p.price)}</span>
        </label>
      </div>

      <button class="btn btn--block" data-add-pdp="${p.id}">Add to bag</button>
      <p class="form-note" style="margin-top:1rem">
        Free shipping over $${FREE_SHIPPING_THRESHOLD} · Ships in 1–2 business days
      </p>

      <h3 style="margin-top:2.5rem">Ingredients</h3>
      <p>${p.ingredients}</p>

      <h3>Guaranteed analysis</h3>
      <ul class="spec-list">
        ${p.analysis.map(([k, v]) => `<li><b>${k}</b><span>${v}</span></li>`).join("")}
      </ul>

      <h3 style="margin-top:2rem">How to feed</h3>
      <p>${p.feeding}</p>

      <ul class="spec-list">
        <li><b>Size</b><span>${p.size}</span></li>
        <li><b>Protein</b><span>${p.protein}</span></li>
      </ul>
    </div>`;

  root.addEventListener("click", (e) => {
    const btn = e.target.closest("[data-add-pdp]");
    if (!btn) return;
    const mode = root.querySelector('input[name="buymode"]:checked').value;
    addToCart(btn.dataset.addPdp, mode, 1);
  });

  const related = document.querySelector("[data-related]");
  if (related) {
    renderGrid(
      related,
      PRODUCTS.filter((x) => x.id !== p.id).slice(0, 4)
    );
  }
}

function initCartPage() {
  const root = document.querySelector("[data-cart-root]");
  if (!root) return;

  function paint() {
    const cart = loadCart();

    if (!cart.length) {
      root.innerHTML = `
        <div class="empty-state">
          <h2>Your bag is empty</h2>
          <p class="lede">Nothing in here yet. The good stuff is one click away.</p>
          <a class="btn" href="shop.html">Shop the range</a>
        </div>`;
      return;
    }

    const subtotal = cartSubtotal();
    const shipping = subtotal >= FREE_SHIPPING_THRESHOLD ? 0 : FLAT_SHIPPING;
    const hasSub = cart.some((l) => l.mode === "sub");

    const lines = cart
      .map((line, i) => {
        const p = getProduct(line.id);
        if (!p) return "";
        const unit = line.mode === "sub" ? subscriptionPrice(p.price) : p.price;
        return `
          <div class="cart-line">
            <div class="thumb">${productMedia(p)}</div>
            <div>
              <h3>${p.name}</h3>
              <div class="meta">${p.size} · ${
          line.mode === "sub" ? "Subscription, every 4 weeks" : "One-time purchase"
        }</div>
              <div style="display:flex;align-items:center;gap:1rem;margin-top:0.6rem">
                <span class="qty">
                  <button data-dec="${i}" aria-label="Decrease quantity">−</button>
                  <span>${line.qty}</span>
                  <button data-inc="${i}" aria-label="Increase quantity">+</button>
                </span>
                <button class="link-danger" data-remove="${i}">Remove</button>
              </div>
            </div>
            <div class="price">${money(unit * line.qty)}</div>
          </div>`;
      })
      .join("");

    const shortfall = FREE_SHIPPING_THRESHOLD - subtotal;

    root.innerHTML = `
      <div class="cart-layout">
        <div>${lines}</div>
        <aside class="summary">
          <h3 class="mt-0">Summary</h3>
          <dl>
            <dt>Subtotal</dt><dd>${money(subtotal)}</dd>
            <dt>Shipping</dt><dd>${shipping === 0 ? "Free" : money(shipping)}</dd>
            <div class="total" style="display:contents">
              <dt>Total</dt><dd>${money(subtotal + shipping)}</dd>
            </div>
          </dl>
          ${
            shortfall > 0
              ? `<p class="form-note">Add ${money(shortfall)} more for free shipping.</p>`
              : `<p class="form-note">You've earned free shipping.</p>`
          }
          ${
            hasSub
              ? `<p class="form-note">Subscription items renew every 4 weeks. Skip or cancel any time from your account.</p>`
              : ""
          }
          <button class="btn btn--block" data-checkout style="margin-top:1rem">Checkout</button>
          <p class="form-note center" style="margin-top:1rem">Secure checkout · Cards &amp; PayPal</p>
        </aside>
      </div>`;
  }

  root.addEventListener("click", (e) => {
    const cart = loadCart();
    const inc = e.target.closest("[data-inc]");
    const dec = e.target.closest("[data-dec]");
    const rm = e.target.closest("[data-remove]");
    const co = e.target.closest("[data-checkout]");

    if (inc) {
      cart[+inc.dataset.inc].qty += 1;
    } else if (dec) {
      const i = +dec.dataset.dec;
      cart[i].qty -= 1;
      if (cart[i].qty < 1) cart.splice(i, 1);
    } else if (rm) {
      cart.splice(+rm.dataset.remove, 1);
    } else if (co) {
      toast("Connect a payment provider to take live orders");
      return;
    } else {
      return;
    }

    saveCart(cart);
    paint();
  });

  paint();
}

/* ------------------------------------------------------------------ forms */

function initForms() {
  document.querySelectorAll("form[data-demo-form]").forEach((form) => {
    form.addEventListener("submit", (e) => {
      e.preventDefault();
      const msg = form.dataset.demoForm || "Thanks — we'll be in touch.";
      form.reset();
      toast(msg);
    });
  });
}

/* -------------------------------------------------------------------- nav */

function initNav() {
  const toggle = document.querySelector("[data-nav-toggle]");
  const panel = document.querySelector("[data-mobile-nav]");
  if (!toggle || !panel) return;
  toggle.addEventListener("click", () => {
    const open = panel.classList.toggle("is-open");
    toggle.setAttribute("aria-expanded", String(open));
  });
}

/* Global add-to-bag delegation for grid cards. */
function initGlobalAdd() {
  document.addEventListener("click", (e) => {
    const btn = e.target.closest("[data-add]");
    if (!btn) return;
    addToCart(btn.dataset.add, "once", 1);
  });
}

/* ------------------------------------------------------------------- boot */

document.addEventListener("DOMContentLoaded", () => {
  paintCartCount();
  initNav();
  initGlobalAdd();
  initHome();
  initShop();
  initProduct();
  initCartPage();
  initForms();

  const yearEl = document.querySelector("[data-year]");
  if (yearEl) yearEl.textContent = new Date().getFullYear();
});
