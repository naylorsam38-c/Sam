/* ==========================================================================
   Chew Cartel — product catalogue
   --------------------------------------------------------------------------
   THIS IS THE ONLY FILE YOU NEED TO EDIT TO PUT THE REAL RANGE ON THE SITE.

   Every product page, the shop grid, the cart and the homepage all read from
   this one array. Replace the objects below with the real SKUs and prices
   from the products folder and the whole site updates.

   Field reference
   ---------------
   id            URL-safe slug. Used as ?id= on product.html. Must be unique.
   name          Product name as it should appear on pack.
   tagline       One line, benefit-first. This is what sells in the grid.
   price         One-time purchase price, in dollars, as a number.
   size          Pack weight or count.
   category      One of: chews | functional | training | bundles
   protein       Primary protein, or "Mixed" for bundles.
   badge         Optional flag on the card: "Best seller", "New", etc. or null.
   badgeStyle    "dark" (default) or "tan" for the high-visibility flag.
   rating        Average star rating, 0-5.
   reviews       Review count.
   benefits      Up to 4 short bullets shown on the product page.
   ingredients   Full ingredient string, exactly as on the label.
   analysis      Guaranteed analysis rows, shown as a spec table.
   feeding       Feeding guidance shown on the product page.
   image         Path to a product photo, or null to use the placeholder mark.

   Subscription pricing is derived, not stored — see SUBSCRIPTION_DISCOUNT
   below. Change the number in one place and every price on the site follows.
   ========================================================================== */

const SUBSCRIPTION_DISCOUNT = 0.15; // 15% off every repeat order

const PRODUCTS = [
  {
    id: "smoked-beef-knuckle",
    name: "Smoked Beef Knuckle",
    tagline: "A long, slow chew that keeps heavy chewers honest for hours.",
    price: 12.0,
    size: "1 bone (4–5 in)",
    category: "chews",
    protein: "Beef",
    badge: "Best seller",
    badgeStyle: "tan",
    rating: 4.8,
    reviews: 214,
    benefits: [
      "Hours of occupation for power chewers",
      "Naturally scrapes plaque as they work",
      "Single ingredient — nothing added",
      "Slow-smoked, never bleached"
    ],
    ingredients: "Beef knuckle bone. That is the entire list.",
    analysis: [
      ["Crude protein (min)", "38%"],
      ["Crude fat (min)", "12%"],
      ["Crude fibre (max)", "2%"],
      ["Moisture (max)", "10%"]
    ],
    feeding: "One bone, supervised. Take it away once it is small enough to swallow whole. Fresh water alongside.",
    image: null
  },
  {
    id: "hip-joint-chews",
    name: "Hip & Joint Soft Chews",
    tagline: "Glucosamine and green-lipped mussel for dogs slowing down on the stairs.",
    price: 28.0,
    size: "60 soft chews",
    category: "functional",
    protein: "Chicken",
    badge: "Vet formulated",
    badgeStyle: "dark",
    rating: 4.7,
    reviews: 168,
    benefits: [
      "Supports cartilage and joint comfort",
      "Green-lipped mussel for natural omega-3",
      "Soft texture for older mouths",
      "Dogs take it as a treat, not a pill"
    ],
    ingredients:
      "Chicken, glucosamine hydrochloride, green-lipped mussel powder, chondroitin sulphate, turmeric, vegetable glycerin, mixed tocopherols (natural preservative).",
    analysis: [
      ["Glucosamine HCl", "300 mg / chew"],
      ["Chondroitin sulphate", "125 mg / chew"],
      ["Green-lipped mussel", "50 mg / chew"],
      ["Moisture (max)", "18%"]
    ],
    feeding: "Under 25 lb: 1 chew daily. 25–75 lb: 2 chews daily. Over 75 lb: 3 chews daily.",
    image: null
  },
  {
    id: "chicken-training-bites",
    name: "Chicken Training Bites",
    tagline: "Pea-sized, high-value and soft — a hundred reps without filling them up.",
    price: 14.0,
    size: "8 oz pouch",
    category: "training",
    protein: "Chicken",
    badge: null,
    badgeStyle: "dark",
    rating: 4.9,
    reviews: 302,
    benefits: [
      "Under 3 calories per bite",
      "Soft enough to swallow fast and keep working",
      "Resealable pouch, no crumbs in your pocket",
      "Two ingredients"
    ],
    ingredients: "Chicken breast, vegetable glycerin.",
    analysis: [
      ["Crude protein (min)", "42%"],
      ["Crude fat (min)", "6%"],
      ["Crude fibre (max)", "1%"],
      ["Calories", "2.8 kcal / bite"]
    ],
    feeding: "Use as a reward during training. Treats should stay under 10% of daily calories.",
    image: null
  },
  {
    id: "dental-sticks",
    name: "Daily Dental Sticks",
    tagline: "A ridged chew that gets at the back molars most brushing misses.",
    price: 18.0,
    size: "28 sticks",
    category: "functional",
    protein: "Sweet potato",
    badge: null,
    badgeStyle: "dark",
    rating: 4.6,
    reviews: 141,
    benefits: [
      "Ridged profile scrubs the gum line",
      "Parsley and mint for fresher breath",
      "Grain free",
      "One a day, no fuss"
    ],
    ingredients:
      "Sweet potato, pea flour, glycerin, parsley, peppermint oil, zinc sulphate, mixed tocopherols (natural preservative).",
    analysis: [
      ["Crude protein (min)", "8%"],
      ["Crude fat (min)", "2%"],
      ["Crude fibre (max)", "5%"],
      ["Moisture (max)", "16%"]
    ],
    feeding: "One stick per day after their evening meal.",
    image: null
  },
  {
    id: "calming-chews",
    name: "Calming Chews",
    tagline: "For thunderstorms, fireworks and the crate they still don't trust.",
    price: 26.0,
    size: "60 soft chews",
    category: "functional",
    protein: "Turkey",
    badge: "New",
    badgeStyle: "dark",
    rating: 4.5,
    reviews: 87,
    benefits: [
      "L-theanine and chamomile for settling",
      "No drowsiness — takes the edge off, not the dog",
      "Works within 30–60 minutes",
      "Safe for daily use"
    ],
    ingredients:
      "Turkey, organic chamomile, L-theanine, passion flower, ginger root, vegetable glycerin, mixed tocopherols (natural preservative).",
    analysis: [
      ["L-theanine", "25 mg / chew"],
      ["Chamomile", "80 mg / chew"],
      ["Crude protein (min)", "22%"],
      ["Moisture (max)", "18%"]
    ],
    feeding: "Give 30–60 minutes ahead of a stressful event. Under 25 lb: 1 chew. 25–75 lb: 2. Over 75 lb: 3.",
    image: null
  },
  {
    id: "bully-sticks-6in",
    name: "Bully Sticks — 6 Inch",
    tagline: "Single-ingredient, odour-controlled, and gone slower than you'd think.",
    price: 24.0,
    size: "10 sticks",
    category: "chews",
    protein: "Beef",
    badge: "Best seller",
    badgeStyle: "tan",
    rating: 4.8,
    reviews: 259,
    benefits: [
      "One ingredient, fully digestible",
      "Low-odour process",
      "Free-range, grass-fed beef",
      "Sized for medium and large dogs"
    ],
    ingredients: "Beef pizzle.",
    analysis: [
      ["Crude protein (min)", "80%"],
      ["Crude fat (min)", "3%"],
      ["Crude fibre (max)", "1%"],
      ["Moisture (max)", "12%"]
    ],
    feeding: "One stick, supervised. Remove the last inch so it can't be swallowed whole.",
    image: null
  },
  {
    id: "salmon-skin-twists",
    name: "Salmon Skin Twists",
    tagline: "Omega-3 straight from the source — for coats that have gone dull.",
    price: 16.0,
    size: "5 oz",
    category: "chews",
    protein: "Salmon",
    badge: null,
    badgeStyle: "dark",
    rating: 4.7,
    reviews: 119,
    benefits: [
      "Natural omega-3 for skin and coat",
      "Crunchy texture dogs work at",
      "Wild-caught, single ingredient",
      "Good for dogs off red meat"
    ],
    ingredients: "Wild-caught salmon skin.",
    analysis: [
      ["Crude protein (min)", "50%"],
      ["Crude fat (min)", "28%"],
      ["Omega-3 fatty acids", "9%"],
      ["Moisture (max)", "10%"]
    ],
    feeding: "One to two twists a day depending on size. Rich in fat — start slow.",
    image: null
  },
  {
    id: "starter-box",
    name: "The Starter Box",
    tagline: "Four of the range at a saving — the easiest way to find their favourite.",
    price: 58.0,
    size: "4 products",
    category: "bundles",
    protein: "Mixed",
    badge: "Save 22%",
    badgeStyle: "tan",
    rating: 4.9,
    reviews: 96,
    benefits: [
      "Smoked Beef Knuckle, Bully Sticks, Training Bites and Dental Sticks",
      "Saves $16 against buying separately",
      "Packed to give as a gift",
      "Swap anything you don't want"
    ],
    ingredients: "See each product for its full ingredient list.",
    analysis: [
      ["Contents", "4 full-size products"],
      ["Value", "$74 if bought separately"],
      ["You save", "$16"],
      ["Shipping", "Free"]
    ],
    feeding: "Follow the guidance on each product.",
    image: null
  }
];

/* Handy lookups used across the site. */
const CATEGORIES = [
  { id: "all", label: "Everything" },
  { id: "chews", label: "Natural chews" },
  { id: "functional", label: "Health & function" },
  { id: "training", label: "Training" },
  { id: "bundles", label: "Bundles" }
];

function getProduct(id) {
  return PRODUCTS.find((p) => p.id === id) || null;
}

function subscriptionPrice(price) {
  return price * (1 - SUBSCRIPTION_DISCOUNT);
}
