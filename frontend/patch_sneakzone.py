#!/usr/bin/env python3
"""
patch_sneakzone_part2.py — applies tasks 5-12 fixes to the sneakzone-ecommerce
repo. Assumes tasks 1-4 are already applied (run patch_sneakzone.py first).

TASKS
  5. products.jsx         — p.name?.toLowerCase() crash guard
  6. cart.jsx + add flow  — deterministic cart doc ID `{uid}_{productId}`,
                            setDoc(..., {merge:true}) + increment(1);
                            navbar badge reads from Firestore (no localStorage drift)
  7. checkOut.jsx         — read cart docs, compute total, writeBatch() that
                            creates an `orders/{uid}_{ts}` doc and clears cart
                            (no card/CVV stored)
  8. profile.jsx          — Auth-first then Firestore; replace updateEmail with
                            verifyBeforeUpdateEmail; reauth moved before any
                            sensitive write
  9. productDetails.jsx   — feedback public read; one-per-user-per-product via
                            doc ID `{productId}_{uid}`; author can edit or delete
 10. App.jsx + main.jsx   — ProtectedRoute wrapper (loading state until
                            onAuthStateChanged fires); 404 route; remove
                            duplicate Bootstrap CSS import from App.jsx
 11. secondnavbar.jsx    — `<a href>` -> `<Link to>`; dropdown uses Bootstrap
                            classes (no hard-coded position); search works on
                            every page (already routed via query string)
 12. signUp.jsx           — remove console.log of credentials; min 8 chars;
                            confirm-password field + match validation; surface
                            Firebase error text

CONSTRAINTS
  - Don't touch src/firebase.js, firebase.json, or Firestore rules.
  - No new dependencies (use only what's already in package.json:
    firebase, react-router-dom, react-bootstrap, react-icons).
  - Match existing code style. No unrelated formatting changes.
  - Idempotent: re-running the script is safe.

USAGE
    python3 patch_sneakzone_part2.py /path/to/sneakzone-ecommerce
    # or, defaulting to the path used in this session:
    python3 patch_sneakzone_part2.py
"""

import sys
import pathlib


REPO_DEFAULT = "/home/z/my-project/sneakzone-ecommerce"


def patch_file(path, edits, label):
    """Apply a list of (old, new, what) or (old, new, what, guard) edits.

    Each edit must match exactly once. The optional 4th element `guard` is a
    substring that, if already present in the file, causes the edit to be
    SKIPPED — this is what makes the script idempotent for edits whose
    replacement contains the original pattern.
    """
    p = pathlib.Path(path)
    if not p.exists():
        print(f"MISS {label}: file not found: {path}")
        return False
    src = p.read_text(encoding="utf-8")
    original = src
    applied = []
    skipped = []
    for edit in edits:
        old, new, what = edit[0], edit[1], edit[2]
        guard = edit[3] if len(edit) > 3 else None
        if guard is not None and guard in src:
            skipped.append(f"{what} (guard present)")
            continue
        if old in src:
            src = src.replace(old, new, 1)
            applied.append(what)
        else:
            skipped.append(f"{what} (pattern missing)")
    if src != original:
        p.write_text(src, encoding="utf-8")
        print(f"OK   {label}: applied {len(applied)} edit(s) -> {', '.join(applied)}")
        if skipped:
            print(f"     (skipped: {', '.join(skipped)})")
        return True
    print(f"NOP  {label}: no changes (already patched?). skipped={skipped}")
    return False


def resolve_src_root(repo_arg):
    """Find the actual `src/` directory under the given repo path.

    Supports two layouts:
      1. Standard:   <repo>/frontend/src/...
      2. Flat:       <repo>/src/...   (running from inside frontend/)
    """
    repo = pathlib.Path(repo_arg).resolve()
    candidates = [
        repo / "frontend" / "src",
        repo / "src",
    ]
    for c in candidates:
        if (c / "Pages" / "productDetails.jsx").exists():
            return c
    return None


# ---------------------------------------------------------------------------
# Task 5 — products.jsx crash guard on missing `name`
# ---------------------------------------------------------------------------
PRODUCTS_EDITS = [
    (
        (
            "  const filteredProducts = products.filter((p) => {\n"
            "    const matchCategory =\n"
            "      selectedCategory === \"all\" || p.category?.toLowerCase() === selectedCategory;\n"
            "    const matchSearch =\n"
            "      p.name.toLowerCase().includes(searchQuery) ||\n"
            "      p.description?.toLowerCase().includes(searchQuery);\n"
            "    return matchCategory && matchSearch;\n"
            "  });\n"
        ),
        (
            "  const filteredProducts = products.filter((p) => {\n"
            "    const matchCategory =\n"
            "      selectedCategory === \"all\" || p.category?.toLowerCase() === selectedCategory;\n"
            "    const matchSearch =\n"
            "      (p.name?.toLowerCase() || \"\").includes(searchQuery) ||\n"
            "      (p.description?.toLowerCase() || \"\").includes(searchQuery);\n"
            "    return matchCategory && matchSearch;\n"
            "  });\n"
        ),
        "Task 5: optional-chain p.name and p.description in filter",
    ),
]


# ---------------------------------------------------------------------------
# Task 6 — cart per-user with deterministic doc ID + increment(quantity)
#
#   The doc ID is `{uid}_{productId}`. We use setDoc(..., {merge:true}) so
#   the first write creates the doc (quantity=1) and subsequent writes
#   just run the merge with increment(1) — atomic, no read-before-write,
#   no duplicates possible.
#
#   Three call sites write to cart:
#     - products.jsx         handleAddToCart(product)
#     - productDetails.jsx   handleAddToCart()  (uses `product` from state)
#
#   We also need `productId` on the doc so cart.jsx can show it / allow
#   quantity edits later. And navBar.jsx must read the count from
#   Firestore (sum of quantities) instead of localStorage, so the badge
#   never drifts.
# ---------------------------------------------------------------------------
PRODUCTS_TASK6_EDITS = [
    # Replace the firestore import to add setDoc, doc, increment.
    (
        'import { collection, getDocs, addDoc } from "firebase/firestore";',
        'import { collection, getDocs, addDoc, setDoc, doc, increment } from "firebase/firestore";',
        "Task 6: import setDoc, doc, increment",
        "increment } from \"firebase/firestore\";",
    ),
    # Rewrite handleAddToCart to use deterministic ID + setDoc merge + increment.
    (
        (
            "  const handleAddToCart = async (product) => {\n"
            "  const user = auth.currentUser;\n"
            "  if (!user) {\n"
            "    alert(\"Please login first!\");\n"
            "    return;\n"
            "  }\n"
            "  try {\n"
            "    await addDoc(collection(db, \"cart\"), {\n"
            "      name: product.name,\n"
            "      price: product.price,\n"
            "      image: product.image,\n"
            "      quantity: 1,\n"
            "      uid: user.uid,\n"
            "    });\n"
            "    //بنجرب للكود يبوظ\n"
            "    let currentCount = parseInt(localStorage.getItem(\"cartCount\")) || 0;\n"
            "    localStorage.setItem(\"cartCount\", currentCount + 1);\n"
            "    window.dispatchEvent(new Event(\"storage\"));\n"
            "\n"
            "    alert(`${product.name} added to cart!`);\n"
            "  } catch (error) {\n"
            "    console.error(\"Error adding to cart: \", error);\n"
            "  }};\n"
        ),
        (
            "  const handleAddToCart = async (product) => {\n"
            "  const user = auth.currentUser;\n"
            "  if (!user) {\n"
            "    alert(\"Please login first!\");\n"
            "    return;\n"
            "  }\n"
            "  try {\n"
            "    // Deterministic doc ID: {uid}_{productId}. setDoc with merge\n"
            "    // means first write creates the doc (quantity=1 via increment),\n"
            "    // subsequent writes atomically bump quantity. No duplicates.\n"
            "    const cartDocId = `${user.uid}_${product.id}`;\n"
            "    await setDoc(doc(db, \"cart\", cartDocId), {\n"
            "      uid: user.uid,\n"
            "      productId: product.id,\n"
            "      name: product.name,\n"
            "      price: product.price,\n"
            "      image: product.image,\n"
            "      quantity: increment(1),\n"
            "    }, { merge: true });\n"
            "\n"
            "    alert(`${product.name} added to cart!`);\n"
            "  } catch (error) {\n"
            "    console.error(\"Error adding to cart: \", error);\n"
            "  }};\n"
        ),
        "Task 6: replace addDoc with deterministic setDoc+merge+increment",
        "const cartDocId = `${user.uid}_${product.id}`;",
    ),
    # `addDoc` is no longer used in products.jsx — remove it from the import
    # so eslint doesn't complain about an unused import.
    # Guard: only apply if `addDoc` is still in the firestore import line.
    (
        'import { collection, getDocs, addDoc, setDoc, doc, increment } from "firebase/firestore";',
        'import { collection, getDocs, setDoc, doc, increment } from "firebase/firestore";',
        "Task 6: drop unused addDoc import",
        # guard: skip if `addDoc` already gone from this specific line.
        # Using a negative-style guard: if the cleaned import already exists,
        # skip. We do this by checking for the cleaned form.
        'import { collection, getDocs, setDoc, doc, increment } from "firebase/firestore";',
    ),
    # `collection` is also no longer used (we use doc/setDoc directly).
    # Leave it — it's still used by the fetch effect at the top of the file.
]


PRODUCT_DETAILS_TASK6_EDITS = [
    # Replace the firestore import to add setDoc, doc, increment.
    # Original (post tasks 1-4) is:
    #   import { doc, getDoc, collection, addDoc, query, where, getDocs, serverTimestamp } from "firebase/firestore";
    (
        'import { doc, getDoc, collection, addDoc, query, where, getDocs, serverTimestamp } from "firebase/firestore";',
        'import { doc, getDoc, collection, addDoc, setDoc, query, where, getDocs, serverTimestamp, increment } from "firebase/firestore";',
        "Task 6: import setDoc + increment",
        "setDoc, query, where, getDocs, serverTimestamp, increment",
    ),
    # Rewrite handleAddToCart body. The original (post tasks 1-4) uses addDoc
    # against collection(db, "cart"). We swap to deterministic setDoc+merge.
    (
        (
            "  // add to cart (per-user; matches products.jsx logic + uid from task 3)\n"
            "  const handleAddToCart = async () => {\n"
            "    const user = auth.currentUser;\n"
            "    if (!user) {\n"
            "      alert(\"Please login first!\");\n"
            "      return;\n"
            "    }\n"
            "    try {\n"
            "      await addDoc(collection(db, \"cart\"), {\n"
            "        name: product.name,\n"
            "        price: product.price,\n"
            "        image: product.image,\n"
            "        quantity: 1,\n"
            "        uid: user.uid,\n"
            "      });\n"
            "      let currentCount = parseInt(localStorage.getItem(\"cartCount\")) || 0;\n"
            "      localStorage.setItem(\"cartCount\", currentCount + 1);\n"
            "      window.dispatchEvent(new Event(\"storage\"));\n"
            "      alert(`${product.name} added to cart!`);\n"
            "    } catch (error) {\n"
            "      console.error(\"Error adding to cart: \", error);\n"
            "    }\n"
            "  };\n"
        ),
        (
            "  // add to cart — deterministic doc ID {uid}_{productId} so duplicates\n"
            "  // are impossible and increment(1) bumps quantity atomically.\n"
            "  const handleAddToCart = async () => {\n"
            "    const user = auth.currentUser;\n"
            "    if (!user) {\n"
            "      alert(\"Please login first!\");\n"
            "      return;\n"
            "    }\n"
            "    try {\n"
            "      const cartDocId = `${user.uid}_${id}`;\n"
            "      await setDoc(doc(db, \"cart\", cartDocId), {\n"
            "        uid: user.uid,\n"
            "        productId: id,\n"
            "        name: product.name,\n"
            "        price: product.price,\n"
            "        image: product.image,\n"
            "        quantity: increment(1),\n"
            "      }, { merge: true });\n"
            "      alert(`${product.name} added to cart!`);\n"
            "    } catch (error) {\n"
            "      console.error(\"Error adding to cart: \", error);\n"
            "    }\n"
            "  };\n"
        ),
        "Task 6: replace addDoc with deterministic setDoc+merge+increment",
        "const cartDocId = `${user.uid}_${id}`;",
    ),
    # `addDoc` is no longer used in productDetails.jsx (feedback now uses setDoc
    # too — see task 9 edits below). But that edit is later in this script.
    # For now, leave addDoc in the import — task 9 will clean it up.
]


# Cart.jsx: add a quantity-stepper UI and a writeDoc path so users can change
# quantity in place. Keeps the existing remove button.
CART_TASK6_EDITS = [
    # Add updateDoc, increment to firestore imports.
    (
        'import { collection, getDocs, deleteDoc, doc, query, where } from "firebase/firestore";',
        'import { collection, getDocs, deleteDoc, doc, query, where, updateDoc, increment } from "firebase/firestore";',
        "Task 6: import updateDoc + increment",
        "updateDoc, increment",
    ),
    # Numeric safety on total: parse price/quantity defensively.
    # Original: `acc + item.price * (item.quantity || 1)` — breaks if `price`
    # is a string ("12.99") because `"12.99" * 1` works but `"12.99" * 0` is 0,
    # and string + number concatenates instead of adding. Force Number().
    (
        (
            "  const calculateTotal = (items) => {\n"
            "    const sum = items.reduce((acc, item) => acc + item.price * (item.quantity || 1), 0);\n"
            "    setTotal(sum);\n"
            "  };\n"
        ),
        (
            "  const calculateTotal = (items) => {\n"
            "    const sum = items.reduce((acc, item) => {\n"
            "      const price = Number(item.price) || 0;\n"
            "      const qty = Number(item.quantity) || 1;\n"
            "      return acc + price * qty;\n"
            "    }, 0);\n"
            "    setTotal(sum);\n"
            "  };\n"
        ),
        "Task 6: numeric-safe total (string-price no longer NaN)",
        "const price = Number(item.price) || 0;",
    ),
    # Add handleUpdateQuantity right after handleRemove so the JSX can call it.
    (
        (
            "  const handleProceed = () => {\n"
            "    navigate(\"/payment\", { state: { total } });\n"
            "  };\n"
        ),
        (
            "  const handleUpdateQuantity = async (id, delta) => {\n"
            "    try {\n"
            "      const itemRef = doc(db, \"cart\", id);\n"
            "      await updateDoc(itemRef, { quantity: increment(delta) });\n"
            "      setCartItems((prev) =>\n"
            "        prev.map((it) =>\n"
            "          it.id === id\n"
            "            ? { ...it, quantity: Math.max(1, (Number(it.quantity) || 1) + delta) }\n"
            "            : it\n"
            "        )\n"
            "      );\n"
            "      // Recompute total from the updated local state.\n"
            "      setCartItems((prev) => {\n"
            "        calculateTotal(prev);\n"
            "        return prev;\n"
            "      });\n"
            "    } catch (error) {\n"
            "      console.error(\"Error updating quantity: \", error);\n"
            "    }\n"
            "  };\n\n"
            "  const handleProceed = () => {\n"
            "    navigate(\"/payment\", { state: { total } });\n"
            "  };\n"
        ),
        "Task 6: add handleUpdateQuantity (increment/decrement via Firestore)",
        "const handleUpdateQuantity = async (id, delta) => {",
    ),
    # Update the JSX card body to show qty stepper and a numeric price display.
    (
        (
            "                  <Card.Body>\n"
            "                    <Card.Title>{item.name}</Card.Title>\n"
            "                    <Card.Text>\n"
            "                      <strong>Price:</strong> ${item.price} <br />\n"
            "                      <strong>Quantity:</strong> {item.quantity || 1}\n"
            "                    </Card.Text>\n"
            "                    <Button\n"
            "                      variant=\"danger\"\n"
            "                      size=\"sm\"\n"
            "                      onClick={() => handleRemove(item.id)}\n"
            "                    >\n"
            "                      Remove\n"
            "                    </Button>\n"
            "                  </Card.Body>\n"
        ),
        (
            "                  <Card.Body>\n"
            "                    <Card.Title>{item.name}</Card.Title>\n"
            "                    <Card.Text>\n"
            "                      <strong>Price:</strong> ${Number(item.price).toFixed(2)} <br />\n"
            "                      <strong>Quantity:</strong>{\" \"}\n"
            "                      <Button\n"
            "                        variant=\"secondary\"\n"
            "                        size=\"sm\"\n"
            "                        onClick={() => handleUpdateQuantity(item.id, -1)}\n"
            "                        disabled={(Number(item.quantity) || 1) <= 1}\n"
            "                      >\n"
            "                        −\n"
            "                      </Button>\n"
            "                      {\" \"}{Number(item.quantity) || 1}{\" \"}\n"
            "                      <Button\n"
            "                        variant=\"secondary\"\n"
            "                        size=\"sm\"\n"
            "                        onClick={() => handleUpdateQuantity(item.id, +1)}\n"
            "                      >\n"
            "                        +\n"
            "                      </Button>\n"
            "                    </Card.Text>\n"
            "                    <Button\n"
            "                      variant=\"danger\"\n"
            "                      size=\"sm\"\n"
            "                      onClick={() => handleRemove(item.id)}\n"
            "                    >\n"
            "                      Remove\n"
            "                    </Button>\n"
            "                  </Card.Body>\n"
        ),
        "Task 6: quantity stepper UI + numeric price display",
        "handleUpdateQuantity(item.id, -1)",
    ),
]


# NavBar.jsx: replace localStorage-based cartCount with a Firestore
# subscription (sum of quantity across the user's cart docs).
NAVBAR_TASK6_EDITS = [
    # Firestore imports: we need collection, query, where, onSnapshot, sum.
    # `onSnapshot` gives us a live subscription; we sum quantity in the reducer.
    (
        'import { auth, onAuthStateChanged } from "../firebase";',
        'import { auth, db, onAuthStateChanged } from "../firebase";',
        "Task 6: import db for cart count subscription",
        "auth, db, onAuthStateChanged",
    ),
    (
        'import { signOut } from "firebase/auth";',
        'import { signOut } from "firebase/auth";\nimport { collection, query, where, onSnapshot } from "firebase/firestore";',
        "Task 6: import firestore onSnapshot for live cart count",
        "import { collection, query, where, onSnapshot } from \"firebase/firestore\";",
    ),
    # Replace the localStorage-based cartCount effect with a Firestore
    # subscription that fires whenever the user's cart docs change.
    (
        (
            "  useEffect(() => {\n"
            "    // لما الصفحة تفتح أو تتحدث، يجيب العدد من localStorage\n"
            "    const count = parseInt(localStorage.getItem(\"cartCount\")) || 0;\n"
            "    setCartCount(count);\n"
            "\n"
            "    // نعمل listener لو العدد اتغير (مثلاً لما نضيف من صفحة تانية)\n"
            "    window.addEventListener(\"storage\", () => {\n"
            "      const updatedCount = parseInt(localStorage.getItem(\"cartCount\")) || 0;\n"
            "      setCartCount(updatedCount);\n"
            "    });\n"
            "  }, []);\n"
        ),
        (
            "  useEffect(() => {\n"
            "    // Subscribe to the cart collection filtered by uid so the badge\n"
            "    // stays in sync with Firestore (no more localStorage drift).\n"
            "    let unsubCart = () => {};\n"
            "    const unsubAuth = onAuthStateChanged(auth, (user) => {\n"
            "      unsubCart();\n"
            "      if (!user) {\n"
            "        setCartCount(0);\n"
            "        return;\n"
            "      }\n"
            "      const q = query(collection(db, \"cart\"), where(\"uid\", \"==\", user.uid));\n"
            "      unsubCart = onSnapshot(q, (snap) => {\n"
            "        const total = snap.docs.reduce(\n"
            "          (acc, d) => acc + (Number(d.get(\"quantity\")) || 1),\n"
            "          0\n"
            "        );\n"
            "        setCartCount(total);\n"
            "      });\n"
            "    });\n"
            "    return () => {\n"
            "      unsubCart();\n"
            "      unsubAuth();\n"
            "    };\n"
            "  }, []);\n"
        ),
        "Task 6: replace localStorage cartCount with Firestore onSnapshot subscription",
        "unsubCart = onSnapshot(q, (snap) => {",
    ),
]


# ---------------------------------------------------------------------------
# Task 12 — signUp.jsx
#   - remove console.log of credentials
#   - min 8 chars (Firebase default is 6; we enforce 8)
#   - confirm-password field + match validation
#   - surface Firebase error text (already done, but make sure)
# ---------------------------------------------------------------------------
SIGNUP_EDITS = [
    # Add a `confirmPassword` state + a `passwordError` state for match errors.
    (
        (
            "  const [name, setName] = useState(\"\");\n"
            "  const [email, setEmail] = useState(\"\");\n"
            "  const [password, setPassword] = useState(\"\");\n"
            "  const [error, setError] = useState(\"\");\n"
        ),
        (
            "  const [name, setName] = useState(\"\");\n"
            "  const [email, setEmail] = useState(\"\");\n"
            "  const [password, setPassword] = useState(\"\");\n"
            "  const [confirmPassword, setConfirmPassword] = useState(\"\");\n"
            "  const [error, setError] = useState(\"\");\n"
        ),
        "Task 12: add confirmPassword state",
        "const [confirmPassword, setConfirmPassword]",
    ),
    # Rewrite handleSubmit to: remove console.logs, enforce length, check match.
    (
        (
            "  const handleSubmit = async (e) => {\n"
            "    e.preventDefault();\n"
            "    console.log(\"Signup submit pressed\", { name, email });\n"
            "\n"
            "    try {\n"
            "      const userCredential = await createUserWithEmailAndPassword(\n"
            "        auth,\n"
            "        email,\n"
            "        password,\n"
            "      );\n"
            "      console.log(\"Firebase createUser result:\", userCredential);\n"
            "      const user = userCredential.user;\n"
            "\n"
            "      await setDoc(doc(db, \"users\", user.uid), {\n"
            "        name: name,\n"
            "        email: email,\n"
            "      });\n"
            "      console.log(\"Saved user to Firestore for uid:\", user.uid);\n"
            "\n"
            "      // Use absolute route (not file path) and replace so back button behaviour is clean\n"
            "      navigate(\"/login\", { replace: true });\n"
            "      console.log(\"navigate('/login') called\");\n"
            "    } catch (err) {\n"
            "      console.error(\"Signup error:\", err);\n"
            "      setError(err.message || \"Signup failed\");\n"
            "    }\n"
            "  };\n"
        ),
        (
            "  const handleSubmit = async (e) => {\n"
            "    e.preventDefault();\n"
            "    setError(\"\");\n"
            "\n"
            "    // Length rule (NIST: length > composition). Firebase's own minimum is 6.\n"
            "    if (password.length < 8) {\n"
            "      setError(\"Password must be at least 8 characters long.\");\n"
            "      return;\n"
            "    }\n"
            "    if (password !== confirmPassword) {\n"
            "      setError(\"Passwords do not match.\");\n"
            "      return;\n"
            "    }\n"
            "\n"
            "    try {\n"
            "      const userCredential = await createUserWithEmailAndPassword(\n"
            "        auth,\n"
            "        email,\n"
            "        password,\n"
            "      );\n"
            "      const user = userCredential.user;\n"
            "\n"
            "      await setDoc(doc(db, \"users\", user.uid), {\n"
            "        name: name,\n"
            "        email: email,\n"
            "      });\n"
            "\n"
            "      // Use absolute route (not file path) and replace so back button behaviour is clean\n"
            "      navigate(\"/login\", { replace: true });\n"
            "    } catch (err) {\n"
            "      // Surface Firebase's own error text (e.g. \"email already in use\").\n"
            "      setError(err.message || \"Signup failed\");\n"
            "    }\n"
            "  };\n"
        ),
        "Task 12: remove console.log, add length+match validation, surface Firebase errors",
        "Password must be at least 8 characters long.",
    ),
    # Add the confirm-password field to the JSX, right after the password field.
    (
        (
            "        <div className=\"form-group\">\n"
            "          <label htmlFor=\"password\">Password</label>\n"
            "          <input\n"
            "            type=\"password\"\n"
            "            id=\"password\"\n"
            "            className=\"form-input\"\n"
            "            placeholder=\"Enter your password\"\n"
            "            value={password}\n"
            "            onChange={(e) => setPassword(e.target.value)}\n"
            "            required\n"
            "          />\n"
            "        </div>\n"
            "        <button type=\"submit\" className=\"signup-btn\">\n"
            "          Sign Up\n"
            "        </button>\n"
            "        {error && <p style={{ color: \"red\" }}>{error}</p>}\n"
        ),
        (
            "        <div className=\"form-group\">\n"
            "          <label htmlFor=\"password\">Password</label>\n"
            "          <input\n"
            "            type=\"password\"\n"
            "            id=\"password\"\n"
            "            className=\"form-input\"\n"
            "            placeholder=\"At least 8 characters\"\n"
            "            value={password}\n"
            "            onChange={(e) => setPassword(e.target.value)}\n"
            "            required\n"
            "            minLength={8}\n"
            "          />\n"
            "        </div>\n"
            "        <div className=\"form-group\">\n"
            "          <label htmlFor=\"confirmPassword\">Confirm Password</label>\n"
            "          <input\n"
            "            type=\"password\"\n"
            "            id=\"confirmPassword\"\n"
            "            className=\"form-input\"\n"
            "            placeholder=\"Re-enter your password\"\n"
            "            value={confirmPassword}\n"
            "            onChange={(e) => setConfirmPassword(e.target.value)}\n"
            "            required\n"
            "            minLength={8}\n"
            "          />\n"
            "        </div>\n"
            "        <button type=\"submit\" className=\"signup-btn\">\n"
            "          Sign Up\n"
            "        </button>\n"
            "        {error && <p style={{ color: \"red\" }}>{error}</p>}\n"
        ),
        "Task 12: add confirm-password field + minLength=8 hint",
        'id=\"confirmPassword\"',
    ),
]


# ---------------------------------------------------------------------------
# Task 7 — checkOut.jsx  (real checkout: compute total from cart docs,
#                              writeBatch order doc + clear cart)
#
#   We do NOT use router state for the total (it can drift). Instead we
#   re-read the user's cart docs in the Checkout component, compute the
#   sum locally, and on submit we use a writeBatch() that:
#     1. writes one `orders/{uid}_{ts}` doc with uid/items/total/status
#     2. deletes each of the user's cart docs
#   All in one atomic batch. We never store card number or CVV anywhere.
# ---------------------------------------------------------------------------
CHECKOUT_EDITS = [
    # Replace the entire file content. Original is short enough that a single
    # full-file replacement is the cleanest approach.
    (
        (
            "import React, { useState } from \"react\";\n"
            "import { Container, Form, Button, Alert } from \"react-bootstrap\";\n"
            "\n"
            "function Checkout() {\n"
            "  const [showSuccess, setShowSuccess] = useState(false);\n"
            "\n"
            "  const handlePayment = (e) => {\n"
            "    e.preventDefault();\n"
            "    setShowSuccess(true);\n"
            "    localStorage.removeItem(\"cart\"); \n"
            "  };\n"
            "\n"
            "  return (\n"
            "    <Container className=\"py-5\">\n"
            "      <h2 className=\"mb-4\">Checkout</h2>\n"
            "      <Form onSubmit={handlePayment}>\n"
            "        <Form.Group className=\"mb-3\">\n"
            "          <Form.Label>Cardholder Name</Form.Label>\n"
            "          <Form.Control type=\"text\" placeholder=\"Enter your name\" required />\n"
            "        </Form.Group>\n"
            "        <Form.Group className=\"mb-3\">\n"
            "          <Form.Label>Card Number</Form.Label>\n"
            "          <Form.Control type=\"text\" placeholder=\"1234 5678 9012 3456\" required />\n"
            "        </Form.Group>\n"
            "        <Form.Group className=\"mb-3\">\n"
            "          <Form.Label>Expiry Date</Form.Label>\n"
            "          <Form.Control type=\"text\" placeholder=\"MM/YY\" required />\n"
            "        </Form.Group>\n"
            "        <Form.Group className=\"mb-3\">\n"
            "          <Form.Label>CVV</Form.Label>\n"
            "          <Form.Control type=\"password\" placeholder=\"***\" required />\n"
            "        </Form.Group>\n"
            "        <Button variant=\"success\" type=\"submit\">\n"
            "          Pay Now\n"
            "        </Button>\n"
            "      </Form>\n"
            "\n"
            "      {showSuccess && (\n"
            "        <Alert variant=\"success\" className=\"mt-4\">\n"
            "          ✅ Payment successful! Thank you for your purchase.\n"
            "        </Alert>\n"
            "      )}\n"
            "    </Container>\n"
            "  );\n"
            "}\n"
            "\n"
            "export default Checkout;\n"
        ),
        (
            "import React, { useEffect, useState } from \"react\";\n"
            "import { Container, Form, Button, Alert, Spinner } from \"react-bootstrap\";\n"
            "import { useNavigate } from \"react-router-dom\";\n"
            "import { auth, db, onAuthStateChanged } from \"../firebase\";\n"
            "import {\n"
            "  collection,\n"
            "  query,\n"
            "  where,\n"
            "  getDocs,\n"
            "  doc,\n"
            "  writeBatch,\n"
            "  serverTimestamp,\n"
            "} from \"firebase/firestore\";\n"
            "\n"
            "function Checkout() {\n"
            "  const [items, setItems] = useState([]);\n"
            "  const [total, setTotal] = useState(0);\n"
            "  const [loading, setLoading] = useState(true);\n"
            "  const [submitting, setSubmitting] = useState(false);\n"
            "  const [showSuccess, setShowSuccess] = useState(false);\n"
            "  const [error, setError] = useState(\"\");\n"
            "  const navigate = useNavigate();\n"
            "\n"
            "  // Re-read the user's cart docs (we do NOT trust router state for the total).\n"
            "  useEffect(() => {\n"
            "    const unsubscribe = onAuthStateChanged(auth, async (user) => {\n"
            "      if (!user) {\n"
            "        setItems([]);\n"
            "        setTotal(0);\n"
            "        setLoading(false);\n"
            "        return;\n"
            "      }\n"
            "      try {\n"
            "        const q = query(collection(db, \"cart\"), where(\"uid\", \"==\", user.uid));\n"
            "        const snap = await getDocs(q);\n"
            "        const docs = snap.docs.map((d) => ({ id: d.id, ...d.data() }));\n"
            "        setItems(docs);\n"
            "        const sum = docs.reduce((acc, it) => {\n"
            "          const price = Number(it.price) || 0;\n"
            "          const qty = Number(it.quantity) || 1;\n"
            "          return acc + price * qty;\n"
            "        }, 0);\n"
            "        setTotal(sum);\n"
            "      } catch (e) {\n"
            "        console.error(\"Checkout load error:\", e);\n"
            "      } finally {\n"
            "        setLoading(false);\n"
            "      }\n"
            "    });\n"
            "    return () => unsubscribe();\n"
            "  }, []);\n"
            "\n"
            "  const handlePayment = async (e) => {\n"
            "    e.preventDefault();\n"
            "    if (items.length === 0) {\n"
            "      setError(\"Your cart is empty.\");\n"
            "      return;\n"
            "    }\n"
            "    setSubmitting(true);\n"
            "    setError(\"\");\n"
            "    try {\n"
            "      const user = auth.currentUser;\n"
            "      if (!user) {\n"
            "        navigate(\"/login\");\n"
            "        return;\n"
            "      }\n"
            "      // One atomic batch: write the order doc, then delete every cart doc.\n"
            "      // We never store card number or CVV anywhere — payment is a mock.\n"
            "      const orderId = `${user.uid}_${Date.now()}`;\n"
            "      const batch = writeBatch(db);\n"
            "      batch.set(doc(db, \"orders\", orderId), {\n"
            "        uid: user.uid,\n"
            "        items: items.map((it) => {\n"
        "          const { id: _ignored, ...rest } = it;\n"
        "          return rest;\n"
        "        }),\n"
            "        total,\n"
            "        status: \"paid\",\n"
            "        createdAt: serverTimestamp(),\n"
            "      });\n"
            "      items.forEach((it) => {\n"
            "        batch.delete(doc(db, \"cart\", it.id));\n"
            "      });\n"
            "      await batch.commit();\n"
            "      setShowSuccess(true);\n"
            "    } catch (err) {\n"
            "      console.error(\"Checkout error:\", err);\n"
            "      setError(err.message || \"Payment failed. Please try again.\");\n"
            "    } finally {\n"
            "      setSubmitting(false);\n"
            "    }\n"
            "  };\n"
            "\n"
            "  if (loading) {\n"
            "    return (\n"
            "      <Container className=\"py-5 text-center\">\n"
            "        <Spinner animation=\"border\" />\n"
            "      </Container>\n"
            "    );\n"
            "  }\n"
            "\n"
            "  if (showSuccess) {\n"
            "    return (\n"
            "      <Container className=\"py-5\">\n"
            "        <Alert variant=\"success\">\n"
            "          ✅ Payment successful! Your order has been placed.\n"
            "        </Alert>\n"
            "        <Button variant=\"primary\" onClick={() => navigate(\"/products\")}>\n"
            "          Continue Shopping\n"
            "        </Button>\n"
            "      </Container>\n"
            "    );\n"
            "  }\n"
            "\n"
            "  return (\n"
            "    <Container className=\"py-5\">\n"
            "      <h2 className=\"mb-4\">Checkout</h2>\n"
            "\n"
            "      {items.length === 0 ? (\n"
            "        <Alert variant=\"info\">\n"
            "          Your cart is empty. <Button variant=\"link\" onClick={() => navigate(\"/products\")}>Browse products</Button>\n"
            "        </Alert>\n"
            "      ) : (\n"
            "        <>\n"
            "          <Alert variant=\"info\" className=\"mb-4\">\n"
            "            <strong>Order Total: ${total.toFixed(2)}</strong> ({items.length} item{items.length > 1 ? \"s\" : \"\"})\n"
            "          </Alert>\n"
            "          <Form onSubmit={handlePayment}>\n"
            "            <Form.Group className=\"mb-3\">\n"
            "              <Form.Label>Cardholder Name</Form.Label>\n"
            "              <Form.Control type=\"text\" placeholder=\"Enter your name\" required />\n"
            "            </Form.Group>\n"
            "            <Form.Group className=\"mb-3\">\n"
            "              <Form.Label>Card Number</Form.Label>\n"
            "              <Form.Control type=\"text\" placeholder=\"1234 5678 9012 3456\" required />\n"
            "              <Form.Text className=\"text-muted\">\n"
            "                Demo only — no real payment is processed and card details are never stored.\n"
            "              </Form.Text>\n"
            "            </Form.Group>\n"
            "            <Form.Group className=\"mb-3\">\n"
            "              <Form.Label>Expiry Date</Form.Label>\n"
            "              <Form.Control type=\"text\" placeholder=\"MM/YY\" required />\n"
            "            </Form.Group>\n"
            "            <Form.Group className=\"mb-3\">\n"
            "              <Form.Label>CVV</Form.Label>\n"
            "              <Form.Control type=\"password\" placeholder=\"***\" required />\n"
            "            </Form.Group>\n"
            "            <Button variant=\"success\" type=\"submit\" disabled={submitting}>\n"
            "              {submitting ? <Spinner as=\"span\" animation=\"border\" size=\"sm\" /> : \"Pay Now\"}\n"
            "            </Button>\n"
            "            {error && <Alert variant=\"danger\" className=\"mt-3\">{error}</Alert>}\n"
            "          </Form>\n"
            "        </>\n"
            "      )}\n"
            "    </Container>\n"
            "  );\n"
            "}\n"
            "\n"
            "export default Checkout;\n"
        ),
        "Task 7: real checkout (re-read cart, writeBatch order + clear cart, no card stored)",
        "writeBatch(db)",
    ),
]


# ---------------------------------------------------------------------------
# Task 8 — profile.jsx  (Auth-first then Firestore; replace deprecated
#                        updateEmail with verifyBeforeUpdateEmail)
#
#   The original flow was:
#     1. reauth (if currentPassword provided)
#     2. updateDoc(users/{uid}, {name})      <-- Firestore first
#     3. updateEmail(user, newEmail)         <-- Auth second (deprecated)
#     4. updatePassword(user, newPassword)
#     5. updateProfile(user, {displayName})
#
#   New flow:
#     1. reauth (if any sensitive change requested) — required for email/password
#     2. updateProfile(user, {displayName})           <-- Auth first (cheap, no email)
#     3. if newPassword -> updatePassword(user, newPassword)
#     4. if newEmail !== user.email ->
#          verifyBeforeUpdateEmail(user, newEmail)    <-- sends verification email,
#                                                          the actual email change
#                                                          happens after the user
#                                                          clicks the link.
#     5. updateDoc(users/{uid}, {name})              <-- Firestore last, only if all
#                                                          Auth writes succeeded.
#
#   verifyBeforeUpdateEmail is the documented replacement for the
#   deprecated updateEmail. It doesn't change the email immediately — it
#   sends a verification link to the NEW address, and the change takes
#   effect when the user clicks it. This is more secure and avoids the
#   "missing recent login" error that updateEmail throws if the user
#   hasn't reauthed recently.
# ---------------------------------------------------------------------------
PROFILE_TASK8_EDITS = [
    # Replace the deprecated import.
    (
        (
            "import {\n"
            "  updateProfile,\n"
            "  updatePassword,\n"
            "  updateEmail,\n"
            "  signOut,\n"
            "  reauthenticateWithCredential,\n"
            "  EmailAuthProvider,\n"
            "} from \"firebase/auth\";\n"
        ),
        (
            "import {\n"
            "  updateProfile,\n"
            "  updatePassword,\n"
            "  verifyBeforeUpdateEmail,\n"
            "  signOut,\n"
            "  reauthenticateWithCredential,\n"
            "  EmailAuthProvider,\n"
            "} from \"firebase/auth\";\n"
        ),
        "Task 8: replace deprecated updateEmail with verifyBeforeUpdateEmail",
        "verifyBeforeUpdateEmail,",
    ),
    # Rewrite handleUpdate so Auth writes happen first and Firestore last.
    (
        (
            "  const handleUpdate = async () => {\n"
            "    const user = auth.currentUser;\n"
            "    if (!user) return alert(\"No user logged in!\");\n"
            "\n"
            "    try {\n"
            "      // لو المستخدم بيغيّر الإيميل أو الباسورد لازم نعمل إعادة مصادقة\n"
            "      if (currentPassword) {\n"
            "        const cred = EmailAuthProvider.credential(user.email, currentPassword);\n"
            "        await reauthenticateWithCredential(user, cred);\n"
            "      }\n"
            "\n"
            "      // تحديث الاسم في Firestore\n"
            "      await updateDoc(doc(db, \"users\", user.uid), { name: newName });\n"
            "\n"
            "      // تحديث الإيميل\n"
            "      if (newEmail && newEmail !== user.email) {\n"
            "        await updateEmail(user, newEmail);\n"
            "      }\n"
            "\n"
            "      // تحديث الباسورد\n"
            "      if (newPassword) {\n"
            "        await updatePassword(user, newPassword);\n"
            "      }\n"
            "\n"
            "      // تحديث الاسم في Firebase Auth\n"
            "      await updateProfile(user, { displayName: newName });\n"
            "\n"
            "      alert(\"✅ Profile updated successfully!\");\n"
            "    } catch (error) {\n"
            "      console.error(\"Error updating profile: \", error);\n"
            "      alert(`⚠️ ${error.message}`);\n"
            "    }\n"
            "  };\n"
        ),
        (
            "  const handleUpdate = async () => {\n"
            "    const user = auth.currentUser;\n"
            "    if (!user) return alert(\"No user logged in!\");\n"
            "\n"
            "    const wantsEmailChange = newEmail && newEmail !== user.email;\n"
            "    const wantsPasswordChange = !!newPassword;\n"
            "    // Email and password changes are sensitive: require reauth.\n"
            "    if ((wantsEmailChange || wantsPasswordChange) && !currentPassword) {\n"
            "      alert(\"Please enter your current password to change email or password.\");\n"
            "      return;\n"
            "    }\n"
            "\n"
            "    try {\n"
            "      // 1) Reauth FIRST if any sensitive change requested.\n"
            "      if (currentPassword) {\n"
            "        const cred = EmailAuthProvider.credential(user.email, currentPassword);\n"
            "        await reauthenticateWithCredential(user, cred);\n"
            "      }\n"
            "\n"
            "      // 2) Auth writes first (cheap; no email change yet).\n"
            "      if (newName) {\n"
            "        await updateProfile(user, { displayName: newName });\n"
            "      }\n"
            "      if (wantsPasswordChange) {\n"
            "        await updatePassword(user, newPassword);\n"
            "      }\n"
            "      if (wantsEmailChange) {\n"
            "        // verifyBeforeUpdateEmail sends a verification link to the NEW\n"
            "        // address. The actual email change happens when the user clicks\n"
            "        // it. This replaces the deprecated updateEmail.\n"
            "        await verifyBeforeUpdateEmail(user, newEmail);\n"
            "      }\n"
            "\n"
            "      // 3) Firestore LAST — only if all Auth writes succeeded.\n"
            "      await updateDoc(doc(db, \"users\", user.uid), { name: newName });\n"
            "\n"
            "      alert(\n"
            "        wantsEmailChange\n"
            "          ? \"✅ Profile updated. Check your NEW email inbox to confirm the email change.\"\n"
            "          : \"✅ Profile updated successfully!\"\n"
            "      );\n"
            "      setCurrentPassword(\"\");\n"
            "      setNewPassword(\"\");\n"
            "    } catch (error) {\n"
            "      console.error(\"Error updating profile: \", error);\n"
            "      alert(`⚠️ ${error.message}`);\n"
            "    }\n"
            "  };\n"
        ),
        "Task 8: Auth-first then Firestore; verifyBeforeUpdateEmail replaces updateEmail",
        "verifyBeforeUpdateEmail(user, newEmail);",
    ),
]


# ---------------------------------------------------------------------------
# Task 9 — productDetails.jsx feedback
#
#   Public read: any visitor sees all feedback for the product.
#   One per user per product: deterministic doc ID `{productId}_{uid}`.
#   Editable / deletable by the author.
#
#   Also fixes the latent bug where `fetchMyFeedback` used
#   `auth.currentUser` directly inside `useEffect` (issue #3 again).
# ---------------------------------------------------------------------------
PRODUCT_DETAILS_TASK9_EDITS = [
    # Swap the import: drop addDoc (no longer needed), add setDoc + deleteDoc.
    # Note: after task 6 the import line is:
    #   import { doc, getDoc, collection, addDoc, setDoc, query, where, getDocs, serverTimestamp, increment } from "firebase/firestore";
    (
        'import { doc, getDoc, collection, addDoc, setDoc, query, where, getDocs, serverTimestamp, increment } from "firebase/firestore";',
        'import { doc, getDoc, collection, setDoc, query, where, getDocs, serverTimestamp, increment, deleteDoc, orderBy } from "firebase/firestore";',
        "Task 9: drop addDoc, add deleteDoc + orderBy",
        "deleteDoc, orderBy",
    ),
    # Add onAuthStateChanged to the firebase import.
    (
        'import { db, auth } from "../firebase";',
        'import { db, auth, onAuthStateChanged } from "../firebase";',
        "Task 9: import onAuthStateChanged for fetchMyFeedback",
        "auth, onAuthStateChanged",
    ),
    # Add state for the public feedback list + author awareness.
    (
        (
            "  const [myFeedback, setMyFeedback] = useState(null);\n"
        ),
        (
            "  const [myFeedback, setMyFeedback] = useState(null);\n"
            "  const [allFeedback, setAllFeedback] = useState([]);\n"
            "  const [currentUid, setCurrentUid] = useState(null);\n"
        ),
        "Task 9: add state for public feedback list + currentUid + editing flag",
        "const [allFeedback, setAllFeedback] = useState([]);",
    ),
    # Subscribe to auth so we know who the current user is (fixes the
    # `auth.currentUser is null on first paint` bug). Also re-fetch public
    # feedback when the product id changes.
    (
        (
            "  // ✅ جلب الفيدباك الخاص بالمستخدم فقط\n"
            "  useEffect(() => {\n"
            "    const fetchMyFeedback = async () => {\n"
            "      const user = auth.currentUser;\n"
            "      if (!user) return;\n"
            "\n"
            "      const q = query(\n"
            "        collection(db, \"feedback\"),\n"
            "        where(\"productId\", \"==\", id),\n"
            "        where(\"userEmail\", \"==\", user.email)\n"
            "      );\n"
            "\n"
            "      const querySnapshot = await getDocs(q);\n"
            "      if (!querySnapshot.empty) {\n"
            "        setMyFeedback(querySnapshot.docs[0].data());\n"
            "      }\n"
            "    };\n"
            "\n"
            "    fetchMyFeedback();\n"
            "  }, [id]);\n"
        ),
        (
            "  // ✅ Track current user (fixes auth.currentUser-null-on-refresh race)\n"
            "  useEffect(() => {\n"
            "    const unsubscribe = onAuthStateChanged(auth, (user) => {\n"
            "      setCurrentUid(user ? user.uid : null);\n"
            "      if (!user) setMyFeedback(null);\n"
            "    });\n"
            "    return () => unsubscribe();\n"
            "  }, []);\n"
            "\n"
            "  // ✅ Fetch ALL public feedback for this product (one render, no auth gate)\n"
            "  useEffect(() => {\n"
            "    const fetchFeedback = async () => {\n"
            "      try {\n"
            "        const q = query(\n"
            "          collection(db, \"feedback\"),\n"
            "          where(\"productId\", \"==\", id),\n"
            "          orderBy(\"createdAt\", \"desc\")\n"
            "        );\n"
            "        const snap = await getDocs(q);\n"
            "        const list = snap.docs.map((d) => ({ id: d.id, ...d.data() }));\n"
            "        setAllFeedback(list);\n"
            "        // Mark the current user's own feedback (if any) for inline editing.\n"
            "        const me = auth.currentUser;\n"
            "        if (me) {\n"
            "          const mine = list.find((f) => f.uid === me.uid);\n"
            "          if (mine) {\n"
            "            setMyFeedback(mine);\n"
            "            setComment(mine.comment);\n"
            "            setRating(mine.rating);\n"
            "          }\n"
            "        }\n"
            "      } catch (e) {\n"
            "        console.error(\"Error fetching feedback:\", e);\n"
            "      }\n"
            "    };\n"
            "    fetchFeedback();\n"
            "  }, [id]);\n"
        ),
        "Task 9: replace fetchMyFeedback with onAuthStateChanged + public feedback fetch",
        "const fetchFeedback = async () => {",
    ),
    # Rewrite handleFeedbackSubmit: deterministic doc ID + setDoc merge
    # (works for both create and edit) + write uid + displayName for display.
    (
        (
            "  // ✅ إرسال الفيدباك\n"
            "  const handleFeedbackSubmit = async () => {\n"
            "    if (!comment || rating === 0) {\n"
            "      alert(\"Please add both a comment and a rating!\");\n"
            "      return;\n"
            "    }\n"
            "\n"
            "    const user = auth.currentUser;\n"
            "    if (!user) {\n"
            "      alert(\"Please login first!\");\n"
            "      return;\n"
            "    }\n"
            "\n"
            "    try {\n"
            "      await addDoc(collection(db, \"feedback\"), {\n"
            "        productId: id,\n"
            "        userEmail: user.email,\n"
            "        comment,\n"
            "        rating,\n"
            "        createdAt: serverTimestamp(),\n"
            "      });\n"
            "\n"
            "      alert(\"Feedback submitted successfully!\");\n"
            "      setMyFeedback({ comment, rating });\n"
            "      setComment(\"\");\n"
            "      setRating(0);\n"
            "    } catch (error) {\n"
            "      console.error(\"Error adding feedback: \", error);\n"
            "    }\n"
            "  };\n"
        ),
        (
            "  // ✅ Submit or update feedback (deterministic doc ID = `{productId}_{uid}`)\n"
            "  const handleFeedbackSubmit = async () => {\n"
            "    if (!comment || rating === 0) {\n"
            "      alert(\"Please add both a comment and a rating!\");\n"
            "      return;\n"
            "    }\n"
            "\n"
            "    const user = auth.currentUser;\n"
            "    if (!user) {\n"
            "      alert(\"Please login first!\");\n"
            "      return;\n"
            "    }\n"
            "\n"
            "    try {\n"
            "      const feedbackId = `${id}_${user.uid}`;\n"
            "      await setDoc(doc(db, \"feedback\", feedbackId), {\n"
            "        productId: id,\n"
            "        uid: user.uid,\n"
            "        userEmail: user.email,\n"
            "        comment,\n"
            "        rating,\n"
            "        updatedAt: serverTimestamp(),\n"
            "      }, { merge: true });\n"
            "\n"
            "      setMyFeedback({ comment, rating });\n"
            "      // Refresh the public list so the new/edited review shows up.\n"
            "      const q = query(\n"
            "        collection(db, \"feedback\"),\n"
            "        where(\"productId\", \"==\", id),\n"
            "        orderBy(\"updatedAt\", \"desc\")\n"
            "      );\n"
            "      const snap = await getDocs(q);\n"
            "      setAllFeedback(snap.docs.map((d) => ({ id: d.id, ...d.data() })));\n"
            "    } catch (error) {\n"
            "      console.error(\"Error saving feedback: \", error);\n"
            "      alert(`⚠️ ${error.message}`);\n"
            "    }\n"
            "  };\n"
            "\n"
            "  const handleDeleteFeedback = async () => {\n"
            "    const user = auth.currentUser;\n"
            "    if (!user) return;\n"
            "    if (!confirm(\"Delete your feedback?\")) return;\n"
            "    try {\n"
            "      const feedbackId = `${id}_${user.uid}`;\n"
            "      await deleteDoc(doc(db, \"feedback\", feedbackId));\n"
            "      setMyFeedback(null);\n"
            "      setComment(\"\");\n"
            "      setRating(0);\n"
            "      setAllFeedback((prev) => prev.filter((f) => f.id !== feedbackId));\n"
            "    } catch (error) {\n"
            "      console.error(\"Error deleting feedback:\", error);\n"
            "      alert(`⚠️ ${error.message}`);\n"
            "    }\n"
            "  };\n"
        ),
        "Task 9: deterministic feedback doc ID; author can edit or delete",
        "const feedbackId = `${id}_${user.uid}`;",
    ),
    # Replace the feedback JSX section: show all public reviews, and show
    # an editable form for the current user's own review (if any).
    (
        (
            "          {/* 📝 Feedback Form */}\n"
            "          <div className=\"feedback-section\">\n"
            "            <h3>Leave Feedback:</h3>\n"
            "\n"
            "            {/* 🌟 Rating Stars */}\n"
            "            <div className=\"star-rating\">\n"
            "              {[...Array(5)].map((star, index) => {\n"
            "                const currentRating = index + 1;\n"
            "                return (\n"
            "                  <span\n"
            "                    key={index}\n"
            "                    className={`star ${currentRating <= (hover || rating) ? \"filled\" : \"\"}`}\n"
            "                    onClick={() => setRating(currentRating)}\n"
            "                    onMouseEnter={() => setHover(currentRating)}\n"
            "                    onMouseLeave={() => setHover(rating)}\n"
            "                  >\n"
            "                    ★\n"
            "                  </span>\n"
            "                );\n"
            "              })}\n"
            "            </div>\n"
            "\n"
            "            <textarea\n"
            "              placeholder=\"Write your feedback...\"\n"
            "              value={comment}\n"
            "              onChange={(e) => setComment(e.target.value)}\n"
            "            />\n"
            "\n"
            "            <button className=\"submit-feedback\" onClick={handleFeedbackSubmit}>\n"
            "              Submit\n"
            "            </button>\n"
            "\n"
            "            {/* ✅ عرض فيدباك المستخدم فقط */}\n"
            "            {myFeedback && (\n"
            "              <div className=\"my-feedback\">\n"
            "                <h4>Your Feedback:</h4>\n"
            "                <p>⭐ {myFeedback.rating}/5</p>\n"
            "                <p>{myFeedback.comment}</p>\n"
            "              </div>\n"
            "            )}\n"
            "          </div>\n"
        ),
        (
            "          {/* 📝 Feedback Section — public reads, author edits */}\n"
            "          <div className=\"feedback-section\">\n"
            "            <h3>{myFeedback ? \"Your Feedback\" : \"Leave Feedback\"}</h3>\n"
            "\n"
            "            {/* Show the form to logged-in users. If they already have a\n"
            "                review, the form pre-fills and the button reads \"Update\". */}\n"
            "            {currentUid ? (\n"
            "              <>\n"
            "                <div className=\"star-rating\">\n"
            "                  {[...Array(5)].map((star, index) => {\n"
            "                    const currentRating = index + 1;\n"
            "                    return (\n"
            "                      <span\n"
            "                        key={index}\n"
            "                        className={`star ${currentRating <= (hover || rating) ? \"filled\" : \"\"}`}\n"
            "                        onClick={() => setRating(currentRating)}\n"
            "                        onMouseEnter={() => setHover(currentRating)}\n"
            "                        onMouseLeave={() => setHover(rating)}\n"
            "                      >\n"
            "                        ★\n"
            "                      </span>\n"
            "                    );\n"
            "                  })}\n"
            "                </div>\n"
            "\n"
            "                <textarea\n"
            "                  placeholder=\"Write your feedback...\"\n"
            "                  value={comment}\n"
            "                  onChange={(e) => setComment(e.target.value)}\n"
            "                />\n"
            "\n"
            "                <button className=\"submit-feedback\" onClick={handleFeedbackSubmit}>\n"
            "                  {myFeedback ? \"Update\" : \"Submit\"}\n"
            "                </button>\n"
            "                {myFeedback && (\n"
            "                  <button\n"
            "                    className=\"submit-feedback\"\n"
            "                    style={{ marginLeft: \"8px\" }}\n"
            "                    onClick={handleDeleteFeedback}\n"
            "                  >\n"
            "                    Delete\n"
            "                  </button>\n"
            "                )}\n"
            "              </>\n"
            "            ) : (\n"
            "              <p>Please log in to leave feedback.</p>\n"
            "            )}\n"
            "\n"
            "            {/* ✅ Public list of all reviews for this product */}\n"
            "            <h4 style={{ marginTop: \"1.5rem\" }}>All Reviews ({allFeedback.length})</h4>\n"
            "            {allFeedback.length === 0 ? (\n"
            "              <p>No reviews yet. Be the first!</p>\n"
            "            ) : (\n"
            "              <ul style={{ listStyle: \"none\", padding: 0 }}>\n"
            "                {allFeedback.map((f) => (\n"
            "                  <li\n"
            "                    key={f.id}\n"
            "                    style={{\n"
            "                      borderBottom: \"1px solid #eee\",\n"
            "                      padding: \"0.5rem 0\",\n"
            "                    }}\n"
            "                  >\n"
            "                    <div>⭐ {f.rating}/5</div>\n"
            "                    <div>{f.comment}</div>\n"
            "                    <small style={{ color: \"#888\" }}>\n"
            "                      by {f.userEmail}\n"
            "                      {f.uid === currentUid ? \" (you)\" : \"\"}\n"
            "                    </small>\n"
            "                  </li>\n"
            "                ))}\n"
            "              </ul>\n"
            "            )}\n"
            "          </div>\n"
        ),
        "Task 9: JSX — public review list + author-editable form + delete button",
        "All Reviews ({allFeedback.length})",
    ),
]


# ---------------------------------------------------------------------------
# Task 10 — App.jsx + main.jsx
#   * Add a ProtectedRoute wrapper that:
#       - shows a loading state until onAuthStateChanged fires
#       - redirects to /login if no user
#   * Wrap /profile, /cart, /payment with ProtectedRoute
#   * Add a 404 route -> NotFound component (inlined in App.jsx)
#   * Remove the duplicate Bootstrap CSS import from App.jsx (already in main.jsx)
#
# Implementation note: we add the ProtectedRoute component + NotFound inline
# in App.jsx so we don't create new files (preserving the existing structure).
# ---------------------------------------------------------------------------
APP_TASK10_EDITS = [
    # Remove the duplicate Bootstrap CSS import from App.jsx (already in main.jsx).
    # No guard: the old_str itself is unique. If already removed, it'll skip via
    # the "pattern missing" path.
    (
        'import "bootstrap/dist/css/bootstrap.min.css";\nimport Cart from "./Pages/cart.jsx";\n',
        'import Cart from "./Pages/cart.jsx";\n',
        "Task 10: remove duplicate Bootstrap CSS import (already in main.jsx)",
    ),
    # Add ProtectedRoute + NotFound inline at the top of App.jsx, after the
    # imports. We import onAuthStateChanged from firebase, plus Spinner from
    # react-bootstrap (already in deps).
    (
        (
            "import Checkout from \"./Pages/checkOut.jsx\";\n"
            "\n"
            "function App() {\n"
        ),
        (
            "import Checkout from \"./Pages/checkOut.jsx\";\n"
            "import { onAuthStateChanged } from \"firebase/auth\";\n"
            "import { auth } from \"./firebase\";\n"
            "import { Spinner } from \"react-bootstrap\";\n"
            "import { Navigate, useLocation } from \"react-router-dom\";\n"
            "import { useEffect, useState } from \"react\";\n"
            "\n"
            "// Route guard: shows a loading state until onAuthStateChanged fires,\n"
            "// then either renders the children or redirects to /login. Without\n"
            "// the loading state, logged-in users would briefly appear logged-out\n"
            "// on refresh and get bounced.\n"
            "function ProtectedRoute({ children }) {\n"
            "  const [state, setState] = useState(\"loading\");\n"
            "  const location = useLocation();\n"
            "  useEffect(() => {\n"
            "    const unsub = onAuthStateChanged(auth, (user) => {\n"
            "      setState(user ? \"authed\" : \"anon\");\n"
            "    });\n"
            "    return () => unsub();\n"
            "  }, []);\n"
            "  if (state === \"loading\") {\n"
            "    return (\n"
            "      <div className=\"d-flex justify-content-center align-items-center\" style={{ minHeight: \"60vh\" }}>\n"
            "        <Spinner animation=\"border\" />\n"
            "      </div>\n"
            "    );\n"
            "  }\n"
            "  if (state === \"anon\") {\n"
            "    return <Navigate to=\"/login\" replace state={{ from: location }} />;\n"
            "  }\n"
            "  return children;\n"
            "}\n"
            "\n"
            "// Simple 404 page with a link home.\n"
            "function NotFound() {\n"
            "  return (\n"
            "    <div className=\"d-flex flex-column align-items-center justify-content-center\" style={{ minHeight: \"60vh\" }}>\n"
            "      <h1 className=\"display-1 fw-bold\">404</h1>\n"
            "      <p className=\"lead\">Page not found.</p>\n"
            "      <a href=\"/\" className=\"btn btn-primary mt-3\">Go home</a>\n"
            "    </div>\n"
            "  );\n"
            "}\n"
            "\n"
            "function App() {\n"
        ),
        "Task 10: add ProtectedRoute + NotFound components",
        "function ProtectedRoute({ children }) {",
    ),
    # Wrap /profile, /cart, /payment with ProtectedRoute and add a 404 route.
    (
        (
            "        <Route path=\"/profile\" element={<Profile />} />\n"
            "        <Route path=\"/products\" element={<Products/>} />\n"
            "        <Route path=\"/product/:id\" element={<ProductDetails />} />\n"
            "        <Route path=\"/cart\" element={<Cart />} />\n"
            "        <Route path=\"/payment\" element={<Checkout />} />\n"
            "      </Routes>\n"
        ),
        (
            "        <Route path=\"/products\" element={<Products/>} />\n"
            "        <Route path=\"/product/:id\" element={<ProductDetails />} />\n"
            "        <Route\n"
            "          path=\"/profile\"\n"
            "          element={\n"
            "            <ProtectedRoute>\n"
            "              <Profile />\n"
            "            </ProtectedRoute>\n"
            "          }\n"
            "        />\n"
            "        <Route\n"
            "          path=\"/cart\"\n"
            "          element={\n"
            "            <ProtectedRoute>\n"
            "              <Cart />\n"
            "            </ProtectedRoute>\n"
            "          }\n"
            "        />\n"
            "        <Route\n"
            "          path=\"/payment\"\n"
            "          element={\n"
            "            <ProtectedRoute>\n"
            "              <Checkout />\n"
            "            </ProtectedRoute>\n"
            "          }\n"
            "        />\n"
            "        <Route path=\"*\" element={<NotFound />} />\n"
            "      </Routes>\n"
        ),
        "Task 10: wrap protected routes + add 404 catch-all",
        "path=\"*\" element={<NotFound />}",
    ),
]

# main.jsx: leave the Bootstrap import alone (it's the canonical one now).
# No edits needed there.


# ---------------------------------------------------------------------------
# Task 11 — secondnavbar.jsx
#   * Replace `<a href>` -> `<Link to>` (no full page reloads)
#   * Replace the hard-coded dropdown position with native Bootstrap dropdown
#     (no portal, no inline `style={{position:'absolute', top:..., left:...}}`)
#   * The search form already routes via navigate(`/products?search=...`) so
#     it works on every page — no change needed there.
# ---------------------------------------------------------------------------
SECONDNAVBAR_TASK11_EDITS = [
    # Add Link import.
    (
        'import { useNavigate } from "react-router-dom";\n',
        'import { useNavigate, Link } from "react-router-dom";\n',
        "Task 11: import Link from react-router-dom",
        "import { useNavigate, Link }",
    ),
    # Replace `<a href="/">Home</a>` etc. with `<Link to="/">...</Link>`.
    (
        '              <a className="nav-link" href="/">Home</a>',
        '              <Link className="nav-link" to="/">Home</Link>',
        "Task 11: Home link -> <Link>",
        '<Link className="nav-link" to="/">Home</Link>',
    ),
    (
        '              <a className="nav-link" href="/products">Products</a>',
        '              <Link className="nav-link" to="/products">Products</Link>',
        "Task 11: Products link -> <Link>",
        '<Link className="nav-link" to="/products">Products</Link>',
    ),
    # Replace the entire Categories dropdown (portal + hard-coded position)
    # with a native Bootstrap dropdown. Drop the `showDropdown` state and the
    # click-outside effect since Bootstrap handles both.
    # We do this in two edits: (a) remove the state/effect, (b) replace the JSX.
    # --- (a) remove state ---
    (
        (
            "  const [searchQuery, setSearchQuery] = useState(\"\");\n"
            "  const [showDropdown, setShowDropdown] = useState(false);\n"
            "  const navigate = useNavigate();\n"
            "\n"
            "  // ✅ Search handler\n"
            "  const handleSearch = (e) => {\n"
            "    e.preventDefault();\n"
            "    if (searchQuery.trim()) {\n"
            "      navigate(`/products?search=${encodeURIComponent(searchQuery)}`);\n"
            "      setSearchQuery(\"\");\n"
            "    }\n"
            "  };\n"
            "\n"
            "  // ✅ Navigate to category directly\n"
            "  const handleCategory = (category) => {\n"
            "    navigate(`/products?category=${category}`);\n"
            "    setShowDropdown(false); // Close dropdown after navigating\n"
            "  };\n"
            "\n"
            "  // ✅ Close dropdown when clicking outside\n"
            "  useEffect(() => {\n"
            "    const handleClickOutside = (event) => {\n"
            "      const dropdown = document.getElementById(\"categoryDropdown\");\n"
            "      if (dropdown && !dropdown.contains(event.target)) {\n"
            "        setShowDropdown(false);\n"
            "      }\n"
            "    };\n"
            "    document.addEventListener(\"click\", handleClickOutside);\n"
            "    return () => document.removeEventListener(\"click\", handleClickOutside);\n"
            "  }, []);\n"
            "\n"
        ),
        (
            "  const [searchQuery, setSearchQuery] = useState(\"\");\n"
            "  const navigate = useNavigate();\n"
            "\n"
            "  // ✅ Search handler\n"
            "  const handleSearch = (e) => {\n"
            "    e.preventDefault();\n"
            "    if (searchQuery.trim()) {\n"
            "      navigate(`/products?search=${encodeURIComponent(searchQuery)}`);\n"
            "      setSearchQuery(\"\");\n"
            "    }\n"
            "  };\n"
            "\n"
            "  // ✅ Navigate to category directly (Bootstrap closes the dropdown\n"
            "  //    for us, so we don't need showDropdown state or click-outside logic.)\n"
            "  const handleCategory = (category) => {\n"
            "    navigate(`/products?category=${category}`);\n"
            "  };\n"
            "\n"
        ),
        "Task 11: remove showDropdown state + click-outside effect (Bootstrap handles it)",
        "//    for us, so we don't need showDropdown state or click-outside logic.",
    ),
    # --- (b) replace the dropdown JSX ---
    (
        (
            "            {/* Categories Dropdown */}\n"
            "            <li className=\"nav-item dropdown\">\n"
            "              <a\n"
            "                className=\"nav-link dropdown-toggle\"\n"
            "                href=\"#\"\n"
            "                id=\"categoryDropdown\"\n"
            "                role=\"button\"\n"
            "                onClick={() => setShowDropdown(!showDropdown)}\n"
            "              >\n"
            "                Categories\n"
            "              </a>\n"
            "\n"
            "              {/* ✅ Render dropdown via Portal */}\n"
            "              {showDropdown &&\n"
            "                ReactDOM.createPortal(\n"
            "                  <ul\n"
            "                    className=\"dropdown-menu show\"\n"
            "                    style={{\n"
            "                      position: \"absolute\",\n"
            "                      top: \"60px\",\n"
            "                      left: \"150px\",\n"
            "                      zIndex: 999999,\n"
            "                    }}\n"
            "                  >\n"
            "                    <li>\n"
            "                      <a\n"
            "                        className=\"dropdown-item\"\n"
            "                        onClick={() => handleCategory(\"men\")}\n"
            "                      >\n"
            "                        Men\n"
            "                      </a>\n"
            "                    </li>\n"
            "                    <li>\n"
            "                      <a\n"
            "                        className=\"dropdown-item\"\n"
            "                        onClick={() => handleCategory(\"women\")}\n"
            "                      >\n"
            "                        Women\n"
            "                      </a>\n"
            "                    </li>\n"
            "                    <li>\n"
            "                      <a\n"
            "                        className=\"dropdown-item\"\n"
            "                        onClick={() => handleCategory(\"kids\")}\n"
            "                      >\n"
            "                        Kids\n"
            "                      </a>\n"
            "                    </li>\n"
            "                  </ul>,\n"
            "                  document.getElementById(\"dropdown-root\")\n"
            "                )}\n"
            "            </li>\n"
        ),
        (
            "            {/* Categories Dropdown — native Bootstrap, no portal */}\n"
            "            <li className=\"nav-item dropdown\">\n"
            "              <a\n"
            "                className=\"nav-link dropdown-toggle\"\n"
            "                href=\"#\"\n"
            "                role=\"button\"\n"
            "                data-bs-toggle=\"dropdown\"\n"
            "                aria-expanded=\"false\"\n"
            "              >\n"
            "                Categories\n"
            "              </a>\n"
            "              <ul className=\"dropdown-menu\">\n"
            "                <li>\n"
            "                  <button\n"
            "                    type=\"button\"\n"
            "                    className=\"dropdown-item\"\n"
            "                    onClick={() => handleCategory(\"men\")}\n"
            "                  >\n"
            "                    Men\n"
            "                  </button>\n"
            "                </li>\n"
            "                <li>\n"
            "                  <button\n"
            "                    type=\"button\"\n"
            "                    className=\"dropdown-item\"\n"
            "                    onClick={() => handleCategory(\"women\")}\n"
            "                  >\n"
            "                    Women\n"
            "                  </button>\n"
            "                </li>\n"
            "                <li>\n"
            "                  <button\n"
            "                    type=\"button\"\n"
            "                    className=\"dropdown-item\"\n"
            "                    onClick={() => handleCategory(\"kids\")}\n"
            "                  >\n"
            "                    Kids\n"
            "                  </button>\n"
            "                </li>\n"
            "              </ul>\n"
            "            </li>\n"
        ),
        "Task 11: replace portal dropdown with native Bootstrap dropdown",
        "data-bs-toggle=\"dropdown\"",
    ),
    # ReactDOM is no longer used — drop the import so eslint stays clean.
    # No guard: the old_str itself is unique. If already removed, it'll skip via
    # the "pattern missing" path.
    (
        'import ReactDOM from "react-dom";\n',
        '',
        "Task 11: drop unused ReactDOM import",
    ),
    # `useEffect` is no longer used in secondnavbar.jsx (we removed the
    # click-outside effect). Drop the import.
    (
        'import React, { useState, useEffect } from "react";\n',
        'import React, { useState } from "react";\n',
        "Task 11: drop unused useEffect import",
        'import React, { useState } from "react";',
    ),
]


# ---------------------------------------------------------------------------
# Main driver
# ---------------------------------------------------------------------------
def main():
    repo_arg = sys.argv[1] if len(sys.argv) > 1 else REPO_DEFAULT
    src = resolve_src_root(repo_arg)

    if src is None:
        repo = pathlib.Path(repo_arg).resolve()
        print(f"Could not find a `src/Pages/productDetails.jsx` under either:")
        print(f"  - {repo / 'frontend' / 'src' / 'Pages' / 'productDetails.jsx'}")
        print(f"  - {repo / 'src' / 'Pages' / 'productDetails.jsx'}")
        sys.exit(1)

    pages = src / "Pages"
    comps = src / "components"

    print(f"Input path: {repo_arg}")
    print(f"Detected src at: {src}\n")

    # Task 5 — products.jsx crash guard
    patch_file(pages / "products.jsx", PRODUCTS_EDITS, "products.jsx (task 5)")

    # Task 6 — deterministic cart doc + increment + quantity stepper +
    #          Firestore-backed navbar badge
    patch_file(pages / "products.jsx", PRODUCTS_TASK6_EDITS, "products.jsx (task 6 add-to-cart)")
    patch_file(pages / "productDetails.jsx", PRODUCT_DETAILS_TASK6_EDITS, "productDetails.jsx (task 6 add-to-cart)")
    patch_file(pages / "cart.jsx", CART_TASK6_EDITS, "cart.jsx (task 6 quantity stepper + numeric total)")
    patch_file(comps / "navBar.jsx", NAVBAR_TASK6_EDITS, "navBar.jsx (task 6 Firestore cart count subscription)")

    # Task 7 — real checkout (writeBatch order + clear cart)
    patch_file(pages / "checkOut.jsx", CHECKOUT_EDITS, "checkOut.jsx (task 7)")

    # Task 8 — profile.jsx Auth-first + verifyBeforeUpdateEmail
    patch_file(pages / "profile.jsx", PROFILE_TASK8_EDITS, "profile.jsx (task 8)")

    # Task 9 — productDetails.jsx public feedback + author edit/delete
    patch_file(pages / "productDetails.jsx", PRODUCT_DETAILS_TASK9_EDITS, "productDetails.jsx (task 9 feedback)")

    # Task 10 — App.jsx route guards + 404 + drop duplicate Bootstrap CSS
    patch_file(src / "App.jsx", APP_TASK10_EDITS, "App.jsx (task 10)")

    # Task 11 — secondnavbar.jsx <Link> + native dropdown
    patch_file(comps / "secondnavbar.jsx", SECONDNAVBAR_TASK11_EDITS, "secondnavbar.jsx (task 11)")

    # Task 12 — signUp.jsx no console.log + min 8 chars + confirm-password
    patch_file(pages / "signUp.jsx", SIGNUP_EDITS, "signUp.jsx (task 12)")

    print("\nDone. Run `npm run build` and `npm run lint` to verify.")


if __name__ == "__main__":
    main()
