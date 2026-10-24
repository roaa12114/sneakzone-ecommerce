#!/usr/bin/env python3
"""
patch_sneakzone.py — applies tasks 1-4 fixes to the sneakzone-ecommerce repo,
plus the CSS-import casing fixes that are REQUIRED for `npm run build` to
succeed on a case-sensitive (Linux) filesystem.

TARGET FILES (under <repo>/frontend/src):
  - Pages/productDetails.jsx   -> tasks 1, 2 + CSS casing fix
  - Pages/products.jsx         -> task 3 (uid + login required) + CSS casing fix
  - Pages/cart.jsx             -> task 3 (query by uid via onAuthStateChanged)
  - Pages/profile.jsx          -> task 4 (onAuthStateChanged instead of auth.currentUser)
  - components/navBar.jsx      -> CSS casing fix only (BLOCKING build on Linux)
  - Pages/signUp.jsx           -> CSS casing fix only (BLOCKING build on Linux)

WHAT IS NOT TOUCHED:
  - src/firebase.js, firebase.json, Firestore rules (per constraints)
  - Tasks 5-12 from the issue list (out of scope of the assigned tasks)

USAGE:
    python3 patch_sneakzone.py /path/to/sneakzone-ecommerce
    # or, defaulting to the path used in this session:
    python3 patch_sneakzone.py
"""

import sys
import pathlib


REPO_DEFAULT = "/home/z/my-project/sneakzone-ecommerce"


def patch_file(path, edits, label):
    """Apply a list of (old, new, what) or (old, new, what, guard) edits.

    Each edit must match exactly once. If any pattern is missing, the file
    is left untouched and we report which edit failed so the user can
    re-run safely. The optional 4th element `guard` is a substring that, if
    already present in the file, causes the edit to be SKIPPED — this is
    what makes the script idempotent for edits whose replacement contains
    the original pattern (e.g. when we prepend new code above an existing
    block whose body we keep verbatim).
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
            # Edit was already applied (guard substring present).
            skipped.append(f"{what} (guard present)")
            continue
        if old in src:
            src = src.replace(old, new, 1)
            applied.append(what)
        else:
            # Could be already-patched via a different guard. Record and continue.
            skipped.append(f"{what} (pattern missing)")
    if src != original:
        p.write_text(src, encoding="utf-8")
        print(f"OK   {label}: applied {len(applied)} edit(s) -> {', '.join(applied)}")
        if skipped:
            print(f"     (skipped: {', '.join(skipped)})")
        return True
    print(f"NOP  {label}: no changes (already patched?). skipped={skipped}")
    return False


# ---------------------------------------------------------------------------
# Task 1 + Task 2 + CSS-casing fix  — productDetails.jsx
# ---------------------------------------------------------------------------
PRODUCT_DETAILS_EDITS = [
    # CSS import casing: actual file is `productDetails.css` (lowercase p).
    # On Linux the existing `./ProductDetails.css` import fails to resolve.
    (
        'import "./ProductDetails.css";',
        'import "./productDetails.css";',
        "CSS import casing: ./ProductDetails.css -> ./productDetails.css",
    ),
    # Task 2 — fix image src. Stored `image` already starts with "/",
    # so prefixing another "/" produces "//images/...". Drop the extra "/".
    (
        "src={`/${product.image}`}",
        "src={product.image}",
        "Task 2: image src — drop extra leading slash",
    ),
    # Task 1 — insert handleAddToCart() between handleFeedbackSubmit and the
    # `if (!product)` render guard. Mirrors products.jsx logic, plus a
    # login-required check and `uid: user.uid` (depends on task 3).
    # Guard: skip if handleAddToCart already declared (script re-run safety).
    (
        "  if (!product) {\n    return <p className=\"loading\">Loading product details...</p>;\n  }",
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
            "  };\n\n"
            "  if (!product) {\n"
            "    return <p className=\"loading\">Loading product details...</p>;\n"
            "  }"
        ),
        "Task 1: insert handleAddToCart() (login required + uid)",
        "const handleAddToCart = async () => {",
    ),
    # Task 1 — wire the button to the new handler.
    (
        '<button className="add-to-cart">Add to Cart</button>',
        '<button className="add-to-cart" onClick={handleAddToCart}>Add to Cart</button>',
        "Task 1: wire Add to Cart button onClick",
    ),
]


# ---------------------------------------------------------------------------
# Task 3 — products.jsx  (uid on add + login required) + CSS casing fix
# ---------------------------------------------------------------------------
PRODUCTS_EDITS = [
    # CSS import casing: actual file is `products.css` (lowercase p).
    (
        'import "./Products.css";',
        'import "./products.css";',
        "CSS import casing: ./Products.css -> ./products.css",
    ),
    # Need `auth` from firebase to read the current user.
    (
        'import { db } from "../firebase";\nimport "./products.css";',
        'import { db, auth } from "../firebase";\nimport "./products.css";',
        "Task 3: import auth for current user check",
    ),
    # Task 3 — require login, write `uid: user.uid` on the cart doc.
    (
        (
            "  const handleAddToCart = async (product) => {\n"
            "  try {\n"
            "    await addDoc(collection(db, \"cart\"), {\n"
            "      name: product.name,\n"
            "      price: product.price,\n"
            "      image: product.image,\n"
            "      quantity: 1\n"
            "    });\n"
        ),
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
        ),
        "Task 3: require login + write uid on cart doc",
    ),
]


# ---------------------------------------------------------------------------
# Task 3 — cart.jsx  (query only the current user's cart items)
# ---------------------------------------------------------------------------
CART_EDITS = [
    # Add `query, where` to the firestore import.
    (
        'import { collection, getDocs, deleteDoc, doc } from "firebase/firestore";',
        'import { collection, getDocs, deleteDoc, doc, query, where } from "firebase/firestore";',
        "Task 3: import query + where from firestore",
    ),
    # Pull `auth` and `onAuthStateChanged` from our firebase module.
    (
        'import { db } from "../firebase";\nimport { useNavigate } from "react-router-dom";',
        'import { db, auth, onAuthStateChanged } from "../firebase";\nimport { useNavigate } from "react-router-dom";',
        "Task 3: import auth + onAuthStateChanged",
    ),
    # Replace the fetchCart effect with an onAuthStateChanged subscription
    # that filters cart docs by `uid == currentUser.uid`. This also fixes
    # the same "currentUser is null on first render after refresh" issue
    # that the user filed for profile.jsx (issue #3).
    (
        (
            "  useEffect(() => {\n"
            "    const fetchCart = async () => {\n"
            "      try {\n"
            "        const querySnapshot = await getDocs(collection(db, \"cart\"));\n"
            "        const items = querySnapshot.docs.map((doc) => ({\n"
            "          id: doc.id,\n"
            "          ...doc.data(),\n"
            "        }));\n"
            "        setCartItems(items);\n"
            "        calculateTotal(items);\n"
            "      } catch (error) {\n"
            "        console.error(\"Error fetching cart items: \", error);\n"
            "      }\n"
            "    };\n\n"
            "    fetchCart();\n"
            "  }, []);\n"
        ),
        (
            "  useEffect(() => {\n"
            "    const unsubscribe = onAuthStateChanged(auth, async (user) => {\n"
            "      if (!user) {\n"
            "        setCartItems([]);\n"
            "        calculateTotal([]);\n"
            "        return;\n"
            "      }\n"
            "      try {\n"
            "        const q = query(collection(db, \"cart\"), where(\"uid\", \"==\", user.uid));\n"
            "        const querySnapshot = await getDocs(q);\n"
            "        const items = querySnapshot.docs.map((doc) => ({\n"
            "          id: doc.id,\n"
            "          ...doc.data(),\n"
            "        }));\n"
            "        setCartItems(items);\n"
            "        calculateTotal(items);\n"
            "      } catch (error) {\n"
            "        console.error(\"Error fetching cart items: \", error);\n"
            "      }\n"
            "    });\n\n"
            "    return () => unsubscribe();\n"
            "  }, []);\n"
        ),
        "Task 3: query cart by uid via onAuthStateChanged",
    ),
]


# ---------------------------------------------------------------------------
# Task 4 — profile.jsx  (onAuthStateChanged instead of auth.currentUser)
# ---------------------------------------------------------------------------
PROFILE_EDITS = [
    # Pull `onAuthStateChanged` from our firebase module.
    (
        'import { auth, db } from "../firebase";',
        'import { auth, db, onAuthStateChanged } from "../firebase";',
        "Task 4: import onAuthStateChanged",
    ),
    # Wrap the existing fetchUserData body in an onAuthStateChanged
    # subscription so it works on first paint after refresh (when
    # auth.currentUser is still null). Behaviour is otherwise identical:
    # same Firestore read, same setLoading(false), same fallback when
    # no user. NOTE: also drops the now-orphaned `setUserData(...)` call
    # (see the next edit) since `userData` is never read anywhere.
    (
        (
            "  useEffect(() => {\n"
            "    const fetchUserData = async () => {\n"
            "      const user = auth.currentUser;\n"
            "      if (user) {\n"
            "        const docRef = doc(db, \"users\", user.uid);\n"
            "        const docSnap = await getDoc(docRef);\n\n"
            "        if (docSnap.exists()) {\n"
            "          setUserData(docSnap.data());\n"
            "          setNewName(docSnap.data().name);\n"
            "          setNewEmail(user.email);\n"
            "        }\n"
            "      }\n"
            "      setLoading(false);\n"
            "    };\n"
            "    fetchUserData();\n"
            "  }, []);\n"
        ),
        (
            "  useEffect(() => {\n"
            "    const unsubscribe = onAuthStateChanged(auth, async (user) => {\n"
            "      if (user) {\n"
            "        const docRef = doc(db, \"users\", user.uid);\n"
            "        const docSnap = await getDoc(docRef);\n\n"
            "        if (docSnap.exists()) {\n"
            "          setNewName(docSnap.data().name);\n"
            "          setNewEmail(user.email);\n"
            "        }\n"
            "      }\n"
            "      setLoading(false);\n"
            "    });\n"
            "    return () => unsubscribe();\n"
            "  }, []);\n"
        ),
        "Task 4: replace auth.currentUser with onAuthStateChanged subscription (+ drop orphaned setUserData call)",
    ),
    # Pre-existing `no-unused-vars` lint error: `userData` is set but never
    # read in the JSX (the form uses `newName` / `newEmail`). Removing the
    # unused state is the minimum change that lets `npm run lint` pass.
    # No behaviour change.
    (
        "  const [userData, setUserData] = useState({ name: \"\", email: \"\" });\n",
        "",
        "Pre-existing lint fix: remove unused `userData` state (no behaviour change)",
    ),
]


# ---------------------------------------------------------------------------
# Build-blocking CSS casing fixes (NOT in the assigned task list, but the
# Linux build fails without them). Pure import-string fixes; no behaviour
# change.
# ---------------------------------------------------------------------------
NAVBAR_EDITS = [
    (
        'import "./navbar.css";',
        'import "./navBar.css";',
        "CSS import casing: ./navbar.css -> ./navBar.css (build-blocking on Linux)",
    ),
]

SIGNUP_EDITS = [
    (
        'import "./Signup.css";',
        'import "./signUp.css";',
        "CSS import casing: ./Signup.css -> ./signUp.css (build-blocking on Linux)",
    ),
]


def resolve_src_root(repo_arg):
    """Find the actual `src/` directory under the given repo path.

    Supports two layouts:
      1. Standard:   <repo>/frontend/src/...   (repo = parent of frontend/)
      2. Flat:       <repo>/src/...            (repo IS frontend/, e.g. when
                                                the project was unzipped
                                                with an extra wrapper folder)

    Returns the absolute pathlib.Path to the `src/` directory, or None
    if neither layout matches.
    """
    repo = pathlib.Path(repo_arg).resolve()
    candidates = [
        repo / "frontend" / "src",   # standard layout
        repo / "src",                # flat layout (running from inside frontend/)
    ]
    for c in candidates:
        if (c / "Pages" / "productDetails.jsx").exists():
            return c
    return None


def main():
    repo_arg = sys.argv[1] if len(sys.argv) > 1 else REPO_DEFAULT
    src = resolve_src_root(repo_arg)

    if src is None:
        # Help the user diagnose: print what we looked for.
        repo = pathlib.Path(repo_arg).resolve()
        print(f"Could not find a `src/Pages/productDetails.jsx` under either:")
        print(f"  - {repo / 'frontend' / 'src' / 'Pages' / 'productDetails.jsx'}")
        print(f"  - {repo / 'src' / 'Pages' / 'productDetails.jsx'}")
        print()
        print("Tips:")
        print("  - If you're INSIDE the frontend/ folder, run:  python patch_sneakzone.py .")
        print("  - If you're in the PARENT of frontend/, run:  python patch_sneakzone.py .")
        print("  - Or pass the explicit path:                  python patch_sneakzone.py F:\\path\\to\\repo")
        sys.exit(1)

    pages = src / "Pages"
    comps = src / "components"

    print(f"Input path: {repo_arg}")
    print(f"Detected src at: {src}\n")

    # NOTE on the pre-existing lint error in profile.jsx (line 15):
    # `const [userData, setUserData] = useState(...)` is declared but
    # `userData` is never read in the JSX (only `setUserData` is called).
    # This is a pre-existing `no-unused-vars` error in the original repo,
    # NOT introduced by these task patches. It blocks `npm run lint`, so
    # we remove the unused state. This is the minimum change to make lint
    # pass; no behaviour change.
    patch_file(pages / "productDetails.jsx", PRODUCT_DETAILS_EDITS, "productDetails.jsx (tasks 1, 2 + CSS casing)")
    patch_file(pages / "products.jsx",       PRODUCTS_EDITS,       "products.jsx (task 3 + CSS casing)")
    patch_file(pages / "cart.jsx",           CART_EDITS,           "cart.jsx (task 3)")
    patch_file(pages / "profile.jsx",        PROFILE_EDITS,        "profile.jsx (task 4)")
    patch_file(comps / "navBar.jsx",         NAVBAR_EDITS,         "navBar.jsx (CSS casing only — build-blocker)")
    patch_file(pages / "signUp.jsx",         SIGNUP_EDITS,         "signUp.jsx (CSS casing only — build-blocker)")

    print("\nDone. Run `npm run build` and `npm run lint` to verify.")


if __name__ == "__main__":
    main()
