# Chew Cartel — retail website

A retail storefront for Chew Cartel, a family dog-treat business that has supplied
the trade since 2005 and is now selling direct to consumers.

Static HTML, CSS and vanilla JavaScript. No build step, no dependencies, no server.
Open `index.html` in a browser and it runs.

## Pages

| File | What it is |
| --- | --- |
| `index.html` | Homepage — hero, best sellers, subscription pitch, story, reviews, email capture |
| `shop.html` | Full range with category filters (`?cat=chews` etc. deep-links a filter) |
| `product.html` | Product detail, driven by `?id=<product-id>` |
| `cart.html` | Bag and order summary |
| `our-story.html` | The twenty-year family story |
| `ingredients.html` | Sourcing, what's never included, feeding and safety |
| `stockists.html` | Trade enquiry form for shops |

## Putting the real products in

**Edit `assets/js/products.js` and nothing else.** Every page reads from the
`PRODUCTS` array in that file — the shop grid, product pages, homepage picks and
the cart all follow automatically. The file documents every field at the top.

Subscription pricing is calculated, not stored. Change `SUBSCRIPTION_DISCOUNT`
at the top of the file and every price on the site updates.

To add product photography, drop images into `assets/img/` and set the `image`
field on a product to its path. Any product with `image: null` falls back to the
placeholder pack mark, so the site never looks broken mid-migration.

## Putting the real logo in

`assets/img/logo.svg` is a **placeholder** rebuilt to match the real badge —
black disc, tan ring, "CHEW" above the dog's head, "CARTEL" below. Replace that
one file with the supplied artwork (keep the filename) and it updates in the
header, footer, hero, favicon and story panel at once.

The palette in `assets/css/site.css` was pulled from the badge: `--ink` for the
black, `--tan` for the gold, `--kraft` and `--bone` for the paper tones. If the
real artwork uses different values, change them in `:root` and the whole site
re-tones.

## Things to confirm before this goes live

These were written as sensible defaults and need checking against reality:

- **"EST. 2005"** on the logo, and the twenty-year timeline throughout.
- **"340+ stockists"** on the homepage and story page.
- **All product copy, ingredients and guaranteed analysis** — currently placeholder.
  Ingredient lists and analysis panels have legal weight; they must match the labels.
- **Reviews on the homepage** are written examples, not real customer reviews.
  Replace them with genuine ones or remove the section — fake reviews carry real
  penalties in the US under the FTC rule on consumer reviews.
- **Shipping terms** ($49 threshold, $6.95 flat rate, 1–2 day dispatch, 30-day refund).
- **The origin of the name** on the story page.

## Going live

The cart is client-side only, held in `localStorage`. The Checkout button is
deliberately inert — it shows a notice rather than pretending to take money.

Two routes from here:

1. **Keep this site, add a payment provider.** Wire the checkout handler in
   `assets/js/site.js` (`data-checkout`) to Stripe Checkout or Shopify Buy Buttons.
   Cheapest, and the design stays exactly as-is.
2. **Port to Shopify.** The subscription mechanics, customer accounts and tax
   handling come for free, which matters once volume is real. This markup and CSS
   translate to a theme directly.

Route 2 is the better long-term answer for a treat business — subscriptions are
where the revenue is, and building that reliably yourself is not worth the time.

The forms (email capture and trade enquiry) currently show a confirmation and
clear. Point them at a real endpoint before launch.

## Local preview

```
python3 -m http.server 8000
```

Then open <http://localhost:8000>. A plain file open works too — the site avoids
`fetch` for exactly that reason.
