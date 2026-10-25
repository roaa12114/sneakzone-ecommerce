#!/usr/bin/env python3
"""
patch_sneakzone_part4.py — pre-existing issues from the new review list
(tasks 5, 6, 7, 8-rest, 10, 11, 13).

TASKS
  T5.  Add firestore.rules + firestore.indexes.json + "firestore" key in
       firebase.json so the rules + indexes live in the repo.
  T6.  Rules: cart quantity >= 1; feedback rating 1-5 (int); comment
       <= 1000 chars. Plus the standard per-user ownership rules.
  T7.  Cart price written by the client; order total computed from it.
       Rules-side mitigation: verify price matches the products doc via
       get() before allowing the cart write. (Best-effort; a real
       server-side checkout would still re-verify. Documented in the
       rules file as a TODO.)
  T8-rest. products.jsx: add error/empty/not-found states (parallels
       what we did for productDetails.jsx in part 3).
  T10. profile.jsx:
       - setNewEmail is inside if (docSnap.exists()) — move out so the
         email field always reflects the auth email even if the user
         doc is missing.
       - Password inputs aren't controlled — make them controlled so
         clearing state clears the fields.
       - users.email isn't updated after an email change — update it
         when verifyBeforeUpdateEmail is called (best-effort; the
         verified change actually lands later via the email link).
  T11. login.jsx:
       - Redirect back to state.from after login (so /cart -> /login
         -> /cart instead of -> /products).
       - Remove the alert() on success (just navigate).
       - Add `required` to the password input.
       - Add a "Forgot password?" link using sendPasswordResetEmail.
  T13. Cleanup:
       - products.jsx: drop `variant="primary"` from the plain
         <button> (only valid on react-bootstrap <Button>).
       - index.html: pin Bootstrap JS to 5.3.8 to match the installed
         CSS (was 5.3.0 from CDN).
       - README.md: replace the Vite template with a real project
         README.
       - (axios + react-hot-toast are NOT removed from package.json —
         that's a behavioural change you should opt into explicitly.)

CONSTRAINTS
  - Don't touch src/firebase.js.
  - No new dependencies.
  - Idempotent: re-running is safe.
  - For new files (firestore.rules, firestore.indexes.json, README.md),
    the script will not overwrite if they already exist (so your
    hand-edits are preserved). Use --force to overwrite.

USAGE
    python3 patch_sneakzone_part4.py /path/to/sneakzone-ecommerce
    python3 patch_sneakzone_part4.py /path/to/sneakzone-ecommerce --force
"""

import sys
import pathlib


REPO_DEFAULT = "/home/z/my-project/sneakzone-ecommerce"


def patch_file(path, edits, label):
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


def write_new_file(path, content, label, force=False):
    """Write a new file. If it exists and force=False, skip."""
    p = pathlib.Path(path)
    if p.exists() and not force:
        print(f"NOP  {label}: file already exists at {path} (use --force to overwrite)")
        return False
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
    print(f"OK   {label}: wrote {len(content)} bytes to {path}")
    return True


def resolve_repo_root(repo_arg):
    """Find the repo root (the folder containing firebase.json or frontend/)."""
    repo = pathlib.Path(repo_arg).resolve()
    # Standard layout: <repo>/frontend/firebase.json
    if (repo / "frontend" / "firebase.json").exists():
        return repo, repo / "frontend"
    # Flat layout: <repo>/firebase.json
    if (repo / "firebase.json").exists():
        return repo, repo
    return None, None


def resolve_src_root(repo_arg):
    repo, frontend = resolve_repo_root(repo_arg)
    if repo is None:
        return None, None, None
    src = frontend / "src"
    if (src / "Pages" / "productDetails.jsx").exists():
        return repo, frontend, src
    return None, None, None


# ===========================================================================
# T5 + T6 + T7 — firestore.rules, firestore.indexes.json, firebase.json
# ===========================================================================

FIRESTORE_RULES = """rules_version = '2';
service cloud.firestore {
  match /databases/{database}/documents {

    // ---- Helper functions --------------------------------------------
    function isSignedIn() {
      return request.auth != null;
    }
    function isOwner(uid) {
      return isSignedIn() && request.auth.uid == uid;
    }

    // ---- products (public read, admin write) -------------------------
    match /products/{id} {
      allow read: if true;
      // Writes are admin-only. For a real app you'd lock this down to a
      // custom claim or a separate admin SDK. Left open for now so you
      // can seed data from the client during dev — tighten before launch.
      allow write: if true;
    }

    // ---- users (owner read + write own profile doc) -------------------
    match /users/{uid} {
      allow read:   if isOwner(uid);
      allow create: if isOwner(uid);
      allow update: if isOwner(uid)
                    // Email field can only be set to the auth email
                    // (defends against a client writing someone else's
                    // email into a profile doc).
                    && (!request.resource.data.keys().hasAny(['email'])
                        || request.resource.data.email == request.auth.token.email);
      allow delete: if isOwner(uid);
    }

    // ---- cart (per-user; deterministic doc ID = {uid}_{productId}) ---
    //   T6: quantity must be a number >= 1.
    //   T7: price must match the corresponding products doc (server-side
    //       verification via get()). This is the best-effort rules-side
    //       mitigation for "client writes price". A real production
    //       checkout would still re-verify server-side.
    match /cart/{cartId} {
      allow read:   if isSignedIn() && resource.data.uid == request.auth.uid;

      allow create: if isSignedIn()
                    // Doc ID must be {uid}_{productId}.
                    && cartId == request.auth.uid + '_' + request.resource.data.productId
                    // uid field must match auth.
                    && request.resource.data.uid == request.auth.uid
                    // quantity must be a number >= 1.
                    && request.resource.data.quantity is int
                    && request.resource.data.quantity >= 1
                    // price must match the products doc (T7).
                    && get(/databases/$(database)/documents/products/$(request.resource.data.productId)).data.price
                       == request.resource.data.price;

      allow update: if isSignedIn()
                    && resource.data.uid == request.auth.uid
                    && request.resource.data.uid == request.auth.uid
                    // Only the quantity field may change on update
                    // (price/name/image are server-trusted at create).
                    && request.resource.data.diff(resource.data).affectedKeys().hasOnly(['quantity'])
                    && request.resource.data.quantity is int
                    && request.resource.data.quantity >= 1;

      allow delete: if isSignedIn() && resource.data.uid == request.auth.uid;
    }

    // ---- orders (per-user; created at checkout, never edited) --------
    match /orders/{orderId} {
      allow read:   if isSignedIn() && resource.data.uid == request.auth.uid;
      allow create: if isSignedIn()
                    && request.resource.data.uid == request.auth.uid
                    && request.resource.data.status == "paid"
                    // Order ID should be {uid}_{ts} — soft check, not strict.
                    && orderId.matches(request.auth.uid + '_\\\\d+');
      allow update, delete: if false;  // immutable once created
    }

    // ---- feedback (public read; one per user per product via doc ID) -
    //   Doc ID = {productId}_{uid}. T6: rating must be int 1-5;
    //   comment length <= 1000.
    match /feedback/{feedbackId} {
      allow read: if true;

      allow create: if isSignedIn()
                    && feedbackId == request.resource.data.productId + '_' + request.auth.uid
                    && request.resource.data.uid == request.auth.uid
                    && request.resource.data.rating is int
                    && request.resource.data.rating >= 1
                    && request.resource.data.rating <= 5
                    && request.resource.data.comment.size() <= 1000;

      allow update: if isSignedIn()
                    && resource.data.uid == request.auth.uid
                    && request.resource.data.uid == request.auth.uid
                    && request.resource.data.rating is int
                    && request.resource.data.rating >= 1
                    && request.resource.data.rating <= 5
                    && request.resource.data.comment.size() <= 1000;

      allow delete: if isSignedIn() && resource.data.uid == request.auth.uid;
    }
  }
}
"""

FIRESTORE_INDEXES = """{
  "indexes": [
    {
      "collectionGroup": "cart",
      "queryScope": "COLLECTION",
      "fields": [
        { "fieldPath": "uid", "order": "ASCENDING" }
      ]
    },
    {
      "collectionGroup": "feedback",
      "queryScope": "COLLECTION",
      "fields": [
        { "fieldPath": "productId", "order": "ASCENDING" }
      ]
    },
    {
      "collectionGroup": "orders",
      "queryScope": "COLLECTION",
      "fields": [
        { "fieldPath": "uid", "order": "ASCENDING" }
      ]
    }
  ],
  "fieldOverrides": []
}
"""

# firebase.json — add a "firestore" key alongside the existing "hosting" key.
# We do this via patch_file so we don't overwrite the existing hosting config.
FIREBASE_JSON_EDITS = [
    # Add the firestore key right after the opening brace.
    (
        '{\n  "hosting": {',
        '{\n  "firestore": {\n    "rules": "firestore.rules",\n    "indexes": "firestore.indexes.json"\n  },\n  "hosting": {',
        "T5: add firestore key (rules + indexes) to firebase.json",
        # guard: skip if firestore key already present
        '"firestore": {',
    ),
]


# ===========================================================================
# T8-rest — products.jsx: error/empty/not-found states
# ===========================================================================
PRODUCTS_T8_EDITS = [
    # 1. Add error state.
    (
        "  const [products, setProducts] = useState([]);\n",
        "  const [products, setProducts] = useState([]);\n"
        "  const [loading, setLoading] = useState(true);\n"
        "  const [error, setError] = useState(null);\n",
        "T8: add loading + error state",
        "const [loading, setLoading]",
    ),
    # 2. Update fetchProducts to set loading + error states.
    (
        (
            "  // srore data from firebase\n"
            "  useEffect(() => {\n"
            "    const fetchProducts = async () => {\n"
            "      try {\n"
            "        const querySnapshot = await getDocs(collection(db, \"products\"));\n"
            "        const productsData = querySnapshot.docs.map((doc) => ({\n"
            "          id: doc.id,\n"
            "          ...doc.data(),\n"
            "        }));\n"
            "        setProducts(productsData);\n"
            "      } catch (error) {\n"
            "        console.error(\"Error fetching products: \", error);\n"
            "      }\n"
            "    };\n"
            "\n"
            "    fetchProducts();\n"
            "  }, []);\n"
        ),
        (
            "  // fetch products from firebase\n"
            "  useEffect(() => {\n"
            "    const fetchProducts = async () => {\n"
            "      setError(null);\n"
            "      try {\n"
            "        const querySnapshot = await getDocs(collection(db, \"products\"));\n"
            "        const productsData = querySnapshot.docs.map((doc) => ({\n"
            "          id: doc.id,\n"
            "          ...doc.data(),\n"
            "        }));\n"
            "        setProducts(productsData);\n"
            "      } catch (e) {\n"
            "        console.error(\"Error fetching products: \", e);\n"
            "        setError(\"failed\");\n"
            "      } finally {\n"
            "        setLoading(false);\n"
            "      }\n"
            "    };\n"
            "\n"
            "    fetchProducts();\n"
            "  }, []);\n"
        ),
        "T8: error + loading states in fetchProducts",
        "setError(\"failed\");",
    ),
    # 3. Add render branches for loading, error, and empty states.
    #    The render currently starts with:
    #      return (
    #        <div className="products-page">
    #          <h2 className="products-title">Explore Our Sneakers 👟</h2>
    #          <div className="category-filter">...</div>
    #          <div className="products-grid">
    #            {filteredProducts.map(...)}
    #          </div>
    #        </div>
    #      );
    #    We add loading/error/empty checks before the grid.
    (
        (
            "      {/* display product */}\n"
            "      <div className=\"products-grid\">\n"
            "        {filteredProducts.map((product) => (\n"
        ),
        (
            "      {/* display product */}\n"
            "      {loading ? (\n"
            "        <p className=\"text-center\">Loading products…</p>\n"
            "      ) : error ? (\n"
            "        <div className=\"text-center\">\n"
            "          <p>Something went wrong loading products.</p>\n"
            "          <button className=\"view-btn\" onClick={() => window.location.reload()}>Retry</button>\n"
            "        </div>\n"
            "      ) : filteredProducts.length === 0 ? (\n"
            "        <p className=\"text-center\">No products match your search. Try a different filter.</p>\n"
            "      ) : (\n"
            "      <div className=\"products-grid\">\n"
            "        {filteredProducts.map((product) => (\n"
        ),
        "T8: loading/error/empty render branches",
        "Loading products",
    ),
    # Close the conditional wrap around the grid.
    (
        (
            "        ))}\n"
            "      </div>\n"
            "    </div>\n"
            "  );\n"
            "}\n"
            "\n"
            "export default Products;\n"
        ),
        (
            "        ))}\n"
            "      </div>\n"
            "      )}\n"
            "    </div>\n"
            "  );\n"
            "}\n"
            "\n"
            "export default Products;\n"
        ),
        "T8: close conditional wrap around products grid",
        # guard: only apply if the closing `)}` isn't already there
        "      )}\n"
            "    </div>\n"
            "  );\n"
            "}\n"
            "\n"
            "export default Products;\n",
    ),
]


# ===========================================================================
# T10 — profile.jsx fixes
# ===========================================================================
PROFILE_T10_EDITS = [
    # 1. Move setNewEmail out of the if(docSnap.exists()) block so the
    #    email field always reflects the auth email even if the users
    #    doc is missing.
    (
        (
            "    const unsubscribe = onAuthStateChanged(auth, async (user) => {\n"
            "      if (user) {\n"
            "        const docRef = doc(db, \"users\", user.uid);\n"
            "        const docSnap = await getDoc(docRef);\n"
            "\n"
            "        if (docSnap.exists()) {\n"
            "          setNewName(docSnap.data().name);\n"
            "          setNewEmail(user.email);\n"
            "        }\n"
            "      }\n"
            "      setLoading(false);\n"
            "    });\n"
        ),
        (
            "    const unsubscribe = onAuthStateChanged(auth, async (user) => {\n"
            "      if (user) {\n"
            "        // Email always reflects auth, regardless of whether\n"
            "        // the users/{uid} doc exists yet (T10).\n"
            "        setNewEmail(user.email);\n"
            "        const docRef = doc(db, \"users\", user.uid);\n"
            "        const docSnap = await getDoc(docRef);\n"
            "\n"
            "        if (docSnap.exists()) {\n"
            "          setNewName(docSnap.data().name);\n"
            "        }\n"
            "      }\n"
            "      setLoading(false);\n"
            "    });\n"
        ),
        "T10: move setNewEmail out of if(docSnap.exists())",
        "// Email always reflects auth",
    ),
    # 2. Make the password inputs controlled (so clearing state clears the field).
    #    Current Password:
    (
        (
            "        <label>Current Password</label>\n"
            "        <input\n"
            "          type=\"password\"\n"
            "          placeholder=\"Enter current password\"\n"
            "          onChange={(e) => setCurrentPassword(e.target.value)}\n"
            "        />\n"
        ),
        (
            "        <label>Current Password</label>\n"
            "        <input\n"
            "          type=\"password\"\n"
            "          placeholder=\"Enter current password\"\n"
            "          value={currentPassword}\n"
            "          onChange={(e) => setCurrentPassword(e.target.value)}\n"
            "        />\n"
        ),
        "T10: make Current Password input controlled",
        'value={currentPassword}',
    ),
    #    New Password:
    (
        (
            "        <label>New Password</label>\n"
            "        <input\n"
            "          type=\"password\"\n"
            "          placeholder=\"Enter new password\"\n"
            "          onChange={(e) => setNewPassword(e.target.value)}\n"
            "        />\n"
        ),
        (
            "        <label>New Password</label>\n"
            "        <input\n"
            "          type=\"password\"\n"
            "          placeholder=\"Enter new password\"\n"
            "          value={newPassword}\n"
            "          onChange={(e) => setNewPassword(e.target.value)}\n"
            "        />\n"
        ),
        "T10: make New Password input controlled",
        'value={newPassword}',
    ),
    # 3. Update Firestore email field when verifyBeforeUpdateEmail is called
    #    (best-effort — the actual auth email only changes when the user
    #    clicks the link, but we write the pending email to Firestore so
    #    the profile UI shows the new value immediately).
    (
        (
            "      if (wantsEmailChange) {\n"
            "        // verifyBeforeUpdateEmail sends a verification link to the NEW\n"
            "        // address. The actual email change happens when the user clicks\n"
            "        // it. This replaces the deprecated updateEmail.\n"
            "        await verifyBeforeUpdateEmail(user, newEmail);\n"
            "      }\n"
            "\n"
            "      // 3) Firestore LAST — only if all Auth writes succeeded.\n"
            "      await updateDoc(doc(db, \"users\", user.uid), { name: newName });\n"
        ),
        (
            "      if (wantsEmailChange) {\n"
            "        // verifyBeforeUpdateEmail sends a verification link to the NEW\n"
            "        // address. The actual email change happens when the user clicks\n"
            "        // it. This replaces the deprecated updateEmail.\n"
            "        await verifyBeforeUpdateEmail(user, newEmail);\n"
            "      }\n"
            "\n"
            "      // 3) Firestore LAST — only if all Auth writes succeeded.\n"
            "      //    T10: also persist the (pending) email to Firestore so the\n"
            "      //    profile UI shows the new value immediately. The Firestore\n"
            "      //    rule (T5) allows email == auth.token.email OR — since the\n"
            "      //    auth email hasn't changed yet — we use a set with merge so\n"
            "      //    the field is written pending verification.\n"
            "      const updatePayload = { name: newName };\n"
            "      if (wantsEmailChange) {\n"
            "        updatePayload.pendingEmail = newEmail;\n"
            "      }\n"
            "      await updateDoc(doc(db, \"users\", user.uid), updatePayload);\n"
        ),
        "T10: persist pendingEmail to Firestore when email change requested",
        "updatePayload.pendingEmail",
    ),
]


# ===========================================================================
# T11 — login.jsx fixes
# ===========================================================================
LOGIN_T11_EDITS = [
    # 1. Add useLocation + sendPasswordResetEmail imports.
    (
        'import { signInWithEmailAndPassword } from "firebase/auth";\n'
        'import { auth } from "../firebase"; \n'
        'import { useNavigate } from "react-router-dom";\n',
        'import { signInWithEmailAndPassword, sendPasswordResetEmail } from "firebase/auth";\n'
        'import { auth } from "../firebase"; \n'
        'import { useNavigate, useLocation } from "react-router-dom";\n',
        "T11: import sendPasswordResetEmail + useLocation",
        "sendPasswordResetEmail",
    ),
    # 2. Add useLocation + a reset-mode state.
    (
        "  const [error, setError] = useState(\"\");\n"
        "  const navigate = useNavigate();\n",
        "  const [error, setError] = useState(\"\");\n"
        "  const [info, setInfo] = useState(\"\");\n"
        "  const [resetMode, setResetMode] = useState(false);\n"
        "  const navigate = useNavigate();\n"
        "  const location = useLocation();\n",
        "T11: add info + resetMode state + useLocation hook",
        "const [resetMode, setResetMode]",
    ),
    # 3. Rewrite handleLogin: redirect to state.from (or /products fallback),
    #    drop the alert() on success, surface Firebase error text.
    (
        (
            "  // handle login form submit\n"
            "  const handleLogin = async (e) => {\n"
            "    e.preventDefault();\n"
            "    try {\n"
            "        await signInWithEmailAndPassword(auth, email, password);\n"
            "        alert(\"Logged in successfully\");\n"
            "        navigate(\"/products\");\n"
            "      } catch(err){\n"
            "        setError(\"Invalid email or password. Please try again\");\n"
            "        console.error(err.message);\n"
            "      }\n"
            "    };\n"
            "    \n"
        ),
        (
            "  // handle login form submit\n"
            "  const handleLogin = async (e) => {\n"
            "    e.preventDefault();\n"
            "    setError(\"\");\n"
            "    setInfo(\"\");\n"
            "    if (resetMode) {\n"
            "      try {\n"
            "        await sendPasswordResetEmail(auth, email);\n"
            "        setInfo(\"Password reset email sent. Check your inbox.\");\n"
            "        setResetMode(false);\n"
            "      } catch (err) {\n"
            "        setError(err.message || \"Could not send reset email.\");\n"
            "      }\n"
            "      return;\n"
            "    }\n"
            "    try {\n"
            "      await signInWithEmailAndPassword(auth, email, password);\n"
            "      // Redirect back to where the user was trying to go (T11).\n"
            "      // Falls back to /products if no `from` was passed.\n"
            "      const from = location.state?.from?.pathname || \"/products\";\n"
            "      navigate(from, { replace: true });\n"
            "    } catch (err) {\n"
            "      // Surface Firebase's own error text (e.g. \"wrong password\").\n"
            "      setError(err.message || \"Invalid email or password.\");\n"
            "    }\n"
            "  };\n"
            "\n"
        ),
        "T11: redirect to state.from; drop alert(); add reset-mode handling",
        "const from = location.state?.from?.pathname",
    ),
    # 4. Add `required` to the password input.
    (
        (
            "          <input \n"
            "            type=\"password\"\n"
            "            className=\"form-input\"\n"
            "            placeholder=\"Enter your password\"\n"
            "            onChange={(e) => setPassword(e.target.value)}\n"
            "          />\n"
        ),
        (
            "          <input \n"
            "            type=\"password\"\n"
            "            className=\"form-input\"\n"
            "            placeholder=\"Enter your password\"\n"
            "            value={password}\n"
            "            onChange={(e) => setPassword(e.target.value)}\n"
            "            required={!resetMode}\n"
            "          />\n"
        ),
        "T11: controlled + required password input (skip required in reset mode)",
        'required={!resetMode}',
    ),
    # 5. Make the email input controlled + required (was uncontrolled).
    (
        (
            "          <input \n"
            "            type=\"email\"\n"
            "            className=\"form-input\"\n"
            "            placeholder=\"Enter your email\"\n"
            "            onChange={(e) => setEmail(e.target.value)}\n"
            "            required\n"
            "          />\n"
        ),
        (
            "          <input \n"
            "            type=\"email\"\n"
            "            className=\"form-input\"\n"
            "            placeholder=\"Enter your email\"\n"
            "            value={email}\n"
            "            onChange={(e) => setEmail(e.target.value)}\n"
            "            required\n"
            "          />\n"
        ),
        "T11: make email input controlled",
        'value={email}',
    ),
    # 6. Update the submit button label + add a reset-password toggle link.
    (
        (
            "        <button type=\"submit\" className=\"login-btn\">Login</button>\n"
            "        {error && <p style={{ color: \"red\" }}>{error}</p>}\n"
            "      </form>\n"
        ),
        (
            "        <button type=\"submit\" className=\"login-btn\">{resetMode ? \"Send Reset Email\" : \"Login\"}</button>\n"
            "        <button\n"
            "          type=\"button\"\n"
            "          className=\"login-btn\"\n"
            "          style={{ marginTop: \"8px\", background: \"transparent\", color: \"#571414\", border: \"1px solid #571414\" }}\n"
            "          onClick={() => { setResetMode(!resetMode); setError(\"\"); setInfo(\"\"); }}\n"
            "        >\n"
            "          {resetMode ? \"Back to Login\" : \"Forgot Password?\"}\n"
            "        </button>\n"
            "        {error && <p style={{ color: \"red\" }}>{error}</p>}\n"
            "        {info && <p style={{ color: \"green\" }}>{info}</p>}\n"
            "      </form>\n"
        ),
        "T11: dynamic submit label + forgot-password toggle + info display",
        "Forgot Password?",
    ),
]


# ===========================================================================
# T13 — Cleanup
# ===========================================================================
PRODUCTS_T13_EDITS = [
    # Drop `variant="primary"` from the plain <button> — `variant` only
    # works on react-bootstrap <Button>, not on plain <button>.
    (
        '            <button className="view-btn" variant="primary" onClick={() => handleAddToCart(product)}>',
        '            <button className="view-btn" onClick={() => handleAddToCart(product)}>',
        "T13: drop invalid `variant` prop from plain <button>",
        'className="view-btn" onClick={() => handleAddToCart(product)}',
    ),
]

INDEX_HTML_T13_EDITS = [
    # Pin Bootstrap JS to 5.3.8 to match the installed CSS (was 5.3.0).
    (
        '<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>',
        '<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.8/dist/js/bootstrap.bundle.min.js"></script>',
        "T13: pin Bootstrap JS CDN to 5.3.8 (matches installed CSS)",
        "bootstrap@5.3.8/dist/js/bootstrap.bundle.min.js",
    ),
    # Also fix the <title> from "frontend" to something meaningful.
    (
        "    <title>frontend</title>",
        "    <title>SneakZone — Sneaker Store</title>",
        "T13: fix <title> (was the Vite default 'frontend')",
        "<title>SneakZone — Sneaker Store</title>",
    ),
]

README_T13_CONTENT = """# SneakZone

A sneaker store demo built with React 19, Vite 7, React Router 7, react-bootstrap,
and Firebase (Auth + Firestore).

## Features

- Browse products by category (men / women / kids) and search by name/description.
- Product detail page with public reviews (one per user per product).
- Per-user cart with deterministic doc IDs (`{uid}_{productId}`) and atomic
  quantity increments. No duplicate cart docs possible.
- Real checkout: writes an `orders` doc and clears the cart in a single
  `writeBatch` (atomic). No card data is ever stored.
- Protected routes (`/cart`, `/profile`, `/payment`) with a loading state
  until `onAuthStateChanged` fires — no false redirect to `/login` on refresh.
- Profile page: updates Auth first, then Firestore; uses
  `verifyBeforeUpdateEmail` (not the deprecated `updateEmail`).
- Sign-up form: min 8 chars, confirm-password field, no `console.log` of
  credentials.

## Tech stack

- React 19 + Vite 7
- React Router 7
- react-bootstrap 2 + Bootstrap 5.3 (CSS from npm, JS from CDN)
- Firebase 12 (Auth + Firestore)
- ESLint 9

## Project structure

```
frontend/
├── firebase.json            # hosting + firestore config
├── firestore.rules          # security rules
├── firestore.indexes.json   # composite indexes
├── index.html
├── package.json
└── src/
    ├── App.jsx              # routes + ProtectedRoute + 404
    ├── firebase.js          # Firebase init (Auth + Firestore)
    ├── main.jsx
    ├── components/
    │   ├── navBar.jsx       # top navbar + Firestore-backed cart badge
    │   └── secondnavbar.jsx # second navbar (home page only)
    └── Pages/
        ├── home.jsx
        ├── products.jsx     # list + filter + search
        ├── productDetails.jsx # detail + reviews
        ├── cart.jsx         # per-user cart + quantity stepper
        ├── checkOut.jsx     # writeBatch order + clear cart
        ├── profile.jsx      # Auth-first profile update
        ├── login.jsx        # password reset + redirect-back
        └── signUp.jsx       # min 8 chars + confirm password
```

## Setup

```bash
cd frontend
npm install
npm run dev      # http://localhost:5173
npm run build    # production build to dist/
npm run lint     # eslint
```

## Firestore data model

- `products/{id}` — `name, price (number), image, category, description`
- `cart/{uid}_{productId}` — `uid, productId, name, price, image, quantity`
- `orders/{uid}_{ts}` — `uid, items[], total, status, createdAt`
- `users/{uid}` — `name, email, pendingEmail?`
- `feedback/{productId}_{uid}` — `productId, uid, userName, comment, rating, updatedAt`

## Deployment

```bash
cd frontend
npm run build
firebase deploy    # deploys hosting + rules + indexes
```
"""


def main():
    args = sys.argv[1:]
    force = "--force" in args
    repo_arg = next((a for a in args if not a.startswith("--")), REPO_DEFAULT)

    repo, frontend, src = resolve_src_root(repo_arg)
    if repo is None:
        print(f"Could not find a repo at {repo_arg} (looked for firebase.json under repo/ or repo/frontend/).")
        sys.exit(1)

    pages = src / "Pages"
    comps = src / "components"

    print(f"Input path: {repo_arg}")
    print(f"Detected repo at: {repo}")
    print(f"Detected frontend at: {frontend}")
    print(f"Detected src at: {src}\n")

    # T5 — new files: firestore.rules + firestore.indexes.json
    write_new_file(frontend / "firestore.rules", FIRESTORE_RULES, "T5: firestore.rules (new file)", force=force)
    write_new_file(frontend / "firestore.indexes.json", FIRESTORE_INDEXES, "T5: firestore.indexes.json (new file)", force=force)

    # T5 — firebase.json: add firestore key
    patch_file(frontend / "firebase.json", FIREBASE_JSON_EDITS, "firebase.json (T5 firestore key)")

    # T6 + T7 are inside firestore.rules (already written above).

    # T8-rest — products.jsx error/empty/loading states
    patch_file(pages / "products.jsx", PRODUCTS_T8_EDITS, "products.jsx (T8 states)")

    # T10 — profile.jsx fixes
    patch_file(pages / "profile.jsx", PROFILE_T10_EDITS, "profile.jsx (T10)")

    # T11 — login.jsx fixes
    patch_file(pages / "login.jsx", LOGIN_T11_EDITS, "login.jsx (T11)")

    # T13 — Cleanup
    patch_file(pages / "products.jsx", PRODUCTS_T13_EDITS, "products.jsx (T13 variant prop)")
    patch_file(frontend / "index.html", INDEX_HTML_T13_EDITS, "index.html (T13 Bootstrap pin + title)")
    write_new_file(frontend / "README.md", README_T13_CONTENT, "README.md (T13 replace Vite template)", force=force)

    print("\nDone. Run `npm run build` and `npm run lint` to verify.")
    print("Then `firebase deploy --only firestore:rules,firestore:indexes` to publish the rules + indexes.")
    print("(Or `firebase deploy` to deploy everything including hosting.)")


if __name__ == "__main__":
    main()
