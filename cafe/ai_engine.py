from __future__ import annotations
import re
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Dict, List, Optional, Tuple
import difflib
from django.db import transaction
from django.db.models import Sum
from .models import Address, Customer, Item, Order, OrderItem, Payment

# ---------- State Management ----------

@dataclass
class AssistantState:
    items: List[Dict] = field(default_factory=list)
    order_type: Optional[str] = None
    last_item: Optional[str] = None  # Tracks last referenced item for context
    details: Dict[str, str] = field(default_factory=dict)
    awaiting_fields: List[str] = field(default_factory=list)
    summary_confirmed: bool = False

    @classmethod
    def from_session(cls, data: Optional[Dict]) -> "AssistantState":
        data = data or {}
        return cls(
            items=list(data.get("items", [])),
            order_type=data.get("order_type"),
            last_item=data.get("last_item"),
            details=dict(data.get("details", {})),
            awaiting_fields=list(data.get("awaiting_fields", [])),
            summary_confirmed=bool(data.get("summary_confirmed", False)),
        )

    def as_dict(self) -> Dict:
        return {
            "items": self.items,
            "order_type": self.order_type,
            "last_item": self.last_item,
            "details": self.details,
            "awaiting_fields": self.awaiting_fields,
            "summary_confirmed": self.summary_confirmed,
        }

    def reset(self) -> None:
        self.items = []
        self.order_type = None
        self.last_item = None
        self.details = {}
        self.awaiting_fields = []
        self.summary_confirmed = False

# ---------- AI Engine Core ----------

class CafeAIEngine:
    # Chat keywords
    ORDER_KEYWORDS = (
        "order", "add", "buy", "need", "want", "get me", "give me", "take", "another", "one more",
    )
    DELIVERY_KEYWORDS = ("deliver", "delivery", "address", "doorstep", "drop", "ship")
    DINING_KEYWORDS = ("dine", "table", "here", "inside", "seat", "dining")
    DINING_FIELDS = ["name", "phone", "table_number"]
    DELIVERY_FIELDS = ["name", "phone", "address_line1", "city", "postal_code"]

    def __init__(self, request):
        self.request = request
        self.message = ""
        self.state = AssistantState.from_session(request.session.get("ai_state"))
        self.menu = self._load_menu()
        self.top_sellers = self._load_top_sellers()

    @staticmethod
    def _has_keywords(text: str, keywords: Tuple[str, ...]) -> bool:
        """Check if any of the keywords are present in the text."""
        return any(keyword in text for keyword in keywords)

    def _detect_order_type(self, text: str) -> None:
        """Detect whether the order type is delivery or dining based on message."""
        if any(keyword in text for keyword in self.DELIVERY_KEYWORDS):
            self.state.order_type = "DELIVERY"
        elif any(keyword in text for keyword in self.DINING_KEYWORDS):
            self.state.order_type = "DINING"

    def handle(self, message: str) -> Dict:
        """
        Main entry point: handles incoming user message and produces a reply dict.
        Covers clearing, best/expensive, menu, budget, order, follow-up context logic.
        """
        self.message = message.strip()
        if not self.message:
            return self._reply("Please type a question about the menu, pricing, or ordering.")

        text = self.message.lower()
        self._detect_order_type(text)

        # --- Cart removal logic ---
        if any(word in text for word in ("remove", "clear", "cancel")):
            to_remove = self._extract_remove_items(text)
            if to_remove:
                for item_id in to_remove:
                    self.state.items = [item for item in self.state.items if item.get("id") != item_id]
                if self.state.items:
                    return self._order_summary("Updated cart after removal:")
                else:
                    self.state.reset()
                    return self._reply("All requested items removed. Your cart is now empty. What would you like to order?")
            elif self.state.items:
                self.state.reset()
                return self._reply("I've cleared your cart. What would you like to order now?")
            return self._reply("Your cart is already empty. What would you like to order?")

        # --- Only/just new order intent (discard previous cart) ---
        if "only" in text or "just" in text:
            self.state.items = []
            if re.search(r"\d", text) or self._match_items(text):
                return self._handle_order_intent(text)

        # --- Awaiting details for order completion ---
        if self.state.awaiting_fields:
            return self._capture_detail_input()

        # --- Best-selling item logic ---
        if self._has_keywords(text, ("best seller", "best-selling", "popular", "trend")):
            return self._best_selling_reply()

        # --- Most expensive item query ---
        if "most expensive" in text or "highest price" in text:
            expensive_item = max(self.menu, key=lambda x: float(x["price"]), default=None)
            if expensive_item:
                self.state.last_item = expensive_item["name"]
                return self._reply(f"The most expensive item is {expensive_item['name']} (₹{expensive_item['price']}). Would you like to order it?")
            return self._reply("Sorry, currently I don't have this information.")

        # --- Best item query, also sets context for follow-up ---
        if "best" in text or "top rated" in text or "best selling" in text:
            if self.top_sellers:
                best = self.top_sellers[0]
                self.state.last_item = best['name']
                return self._reply(f"Our best selling item right now is {best['name']}. Would you like to know its price or add it to your cart?")
            return self._reply("Sorry, currently I don't have this information.")

        # --- Handle price queries contextually/professionally ---
        if "price" in text:
            probable_item = self._get_item_from_text(text)
            if not probable_item and self.state.last_item:
                probable_item = self.state.last_item
            if probable_item:
                for item in self.menu:
                    if probable_item.lower() == item["name"].lower():
                        self.state.last_item = item["name"]
                        return self._reply(f"The price of {item['name']} is ₹{item['price']}. Would you like to add it to your cart?")
                return self._reply("Sorry, price information not found for that item.")
            return self._reply("Which item would you like the price for? Please specify.")

        # --- Budget-based suggestions ---
        if self._is_budget_query(text):
            return self._budget_reply(text)

        # --- Menu display: full menu, or category menu if specified/fuzzy matched ---
        if "menu" in text:
            if "category" in text or self._mentions_category(text):
                return self._category_reply(text)
            else:
                return self._full_menu_overview()

        # --- Flavour/type/availability queries; fuzzy match with category names ---
        if "flavour" in text or "type" in text or "available" in text:
            for cat in self._category_names():
                if cat.lower() in text:
                    items = [m for m in self.menu if (m["category__name"] or "").lower() == cat.lower()]
                    listing = ", ".join(f"{m['name']} (₹{m['price']})" for m in items)
                    return self._reply(f"In {cat}, we have: {listing}.")
            return self._full_menu_overview()

        # --- intro and end + Show summary/cart ---
        # if "hello" or "Hello" in text:
        #     return self._reply("Hi! I have limited permission and abilities however order, menu or pricing related issues are pea nuts for me 😉. Please tell me how can I help you?")
        # if "Thanks" or "thanks" in text:
        #     return ("I am glad! 😌") 

        if "Hello" in text or "hello" in text:
            return self._reply("Hi! I have limited permission and abilities however order, menu or pricing related issues are pea nuts for me 😉. Please tell me how can I help you?")
        if "Thanks" in text or "thanks" in text or "thank you" in text or "Thank you" in text:
            return self._reply("I am glad! 😌")
        if "summary" in text or "cart" in text:
            return self._order_summary()

        # --- Reset/clear ---
        if "reset" in text or "clear" in text:
            self.state.reset()
            return self._reply("Your AI cart is now empty. What would you like to order?")

        # --- Confirm/checkout ---
        if "confirm" in text:
            self.state.summary_confirmed = True
            return self._finalize_order()

        # --- Order placement logic via keywords and item matching ---
        if self._has_order_intent(text):
            return self._handle_order_intent(text)

        # --- Fallback generic help reply ---
        return self._reply(
            "I can show best sellers, the full menu, suggest items by budget or category, and place orders. What would you like to do?"
        )

    # ---------- Utility & Data Access Methods ----------

    def persist(self) -> None:
        """Persist current assistant state in user session."""
        self.request.session["ai_state"] = self.state.as_dict()
        self.request.session.modified = True

    def _load_menu(self) -> List[Dict]:
        """Load all active menu items from the database."""
        qs = (
            Item.objects.filter(is_active=True)
            .select_related("category")
            .values("id", "name", "price", "description", "category__name")
            .order_by("category__display_order", "name")
        )
        return list(qs)

    def _load_top_sellers(self) -> List[Dict]:
        """Find top-selling items for highlights (from OrderItem table)."""
        top_qs = (
            OrderItem.objects.values("item_id", "item__name")
            .annotate(total_qty=Sum("quantity"))
            .order_by("-total_qty")[:5]
        )
        return [
            {"id": row["item_id"], "name": row["item__name"], "total": row["total_qty"]}
            for row in top_qs if row["item_id"]
        ]

    def _best_selling_reply(self) -> Dict:
        """Reply with best sellers, for generic highlight queries."""
        if not self.top_sellers:
            preview = ", ".join(f"{m['name']} (₹{m['price']})" for m in self.menu[:3])
            return self._reply(f"Our current highlights are: {preview}. Would you like to add any of them?")
        names = ", ".join(f"{row['name']}" for row in self.top_sellers)
        return self._reply(f"Our best sellers right now are {names}. Should I add one to your order?")

    def _is_budget_query(self, text: str) -> bool:
        """Detect budget queries using regex."""
        return "budget" in text or bool(re.search(r"(under|below|less than)\s*\d+", text))

    def _budget_reply(self, text: str) -> Dict:
        """Suggest items below a user-specified price ceiling."""
        match = re.search(r"(\d+)(?:\s*rs|₹)?", text)
        if not match:
            return self._reply("Share your target budget (e.g., 'under 150') and I'll suggest items.")
        ceiling = float(match.group(1))
        filtered = [m for m in self.menu if float(m["price"]) <= ceiling]
        if not filtered:
            return self._reply(f"I don't have anything under ₹{ceiling:.0f}. Try a higher budget?")
        preview = ", ".join(f"{m['name']} (₹{m['price']})" for m in filtered[:6])
        return self._reply(f"Within ₹{ceiling:.0f}, you could try {preview}. Want me to add any of these?")

    def _mentions_category(self, text: str) -> bool:
        """Return True if a category or its fuzzy match is in the message."""
        categories = self._category_names()
        text_lower = text.lower()
        probable_cat = difflib.get_close_matches(
            text_lower, [cat.lower() for cat in categories], n=1, cutoff=0.7
        )
        return any(cat.lower() in text_lower or (probable_cat and cat.lower() == probable_cat[0]) for cat in categories if cat)

    def _category_reply(self, text: str) -> Dict:
        """
        Show items in a specific category,
        robust to spelling errors ("dessrt" for "dessert", etc.).
        """
        categories = self._category_names()
        text_lower = text.lower()
        probable_cat = difflib.get_close_matches(
            text_lower, [cat.lower() for cat in categories], n=1, cutoff=0.7
        )
        for cat in categories:
            if cat and (cat.lower() in text_lower or (probable_cat and cat.lower() == probable_cat[0])):
                items = [m for m in self.menu if (m["category__name"] or "").lower() == cat.lower()]
                listing = ", ".join(f"{m['name']} (₹{m['price']})" for m in items)
                return self._reply(f"In {cat}, we have {listing}. Would you like to add any of them?")
        cats = ", ".join(categories)
        return self._reply(f"We offer categories such as {cats}. Ask me for any category to see recommendations.")

    def _full_menu_overview(self) -> Dict:
        """Show the complete menu as a single reply."""
        listing = ", ".join(f"{itm['name']} (₹{itm['price']})" for itm in self.menu)
        return self._reply(f"Our menu:\n{listing}")

    def _category_names(self) -> List[str]:
        """Get all available category names in sorted order."""
        return sorted({row["category__name"] or "Others" for row in self.menu})

    def _has_order_intent(self, text: str) -> bool:
        """Detect if the user wishes to place or update an order."""
        return any(keyword in text for keyword in self.ORDER_KEYWORDS)

    def _handle_order_intent(self, text: str) -> Dict:
        """Parse and handle user messages with ordering intent."""
        matched = self._match_items(text)
        if not matched:
            return self._reply("I couldn't find that item. Try 'order 1 cappuccino' or 'add veg biryani x2'.")
        for item_id, qty in matched:
            menu_item = next((m for m in self.menu if m["id"] == item_id), None)
            if not menu_item:
                continue
            existing = next((row for row in self.state.items if row["id"] == item_id), None)
            if existing:
                existing["qty"] += qty
            else:
                self.state.items.append({
                    "id": item_id,
                    "name": menu_item["name"],
                    "qty": qty,
                    "price": float(menu_item["price"]),
                })
            self.state.last_item = menu_item["name"]
        return self._order_summary("Great choice! Here's your updated cart:")

    def _get_item_from_text(self, text: str) -> Optional[str]:
        """
        Detect which item is mentioned in the user’s text, robust to typos.
        Uses fuzzy matching.
        """
        text_lower = self._fix_typos(text.lower())
        item_names = [item["name"].lower() for item in self.menu]
        for name in item_names:
            if name in text_lower:
                return name
        probable_item = difflib.get_close_matches(text_lower, item_names, n=1, cutoff=0.7)
        if probable_item:
            return probable_item[0]
        return None

    def _match_items(self, text: str) -> List[Tuple[int, int]]:
        """
        Find and return items matched in the message,
        with quantity handling and typo correction.
        """
        matches: List[Tuple[int, int]] = []
        text_lower = self._fix_typos(text.lower())
        seen_ids = set()

        for item in self.menu:
            name = item["name"].lower()
            words = [w for w in name.split() if len(w) > 2]
            qty = 0
            # Direct substring / word matches
            if name in text_lower or all(w in text_lower for w in words):
                qty = self._extract_quantity(text_lower, words[-1] if words else name)
            else:
                best_match = difflib.get_close_matches(name, [text_lower], n=1, cutoff=0.7)
                if best_match:
                    qty = self._extract_quantity(text_lower, words[-1] if words else name)
            if qty and item["id"] not in seen_ids:
                matches.append((item["id"], qty))
                seen_ids.add(item["id"])
        return matches

    def _fix_typos(self, text: str) -> str:
        """Correct common spelling mistakes in item names within messages."""
        typo_map = {
            "coffe": "coffee",
            "cofee": "coffee",
            "expresso": "espresso",
            "mocctail": "mocktail",
            "mojitoo": "mojito",
            "samosaa": "samosa",
            "samos": "samosa",
            "latte": "latte",
            "lattte": "latte",
            "capuccino": "cappuccino",
            "capucino": "cappuccino",
            "piza": "pizza",
        }
        for wrong, correct in typo_map.items():
            text = re.sub(rf"\b{re.escape(wrong)}\b", correct, text)
        return text

    def _extract_quantity(self, text: str, token: str) -> int:
        """Extract numerical quantity for an order given a matched token."""
        pattern = rf"(\d+)\s+{re.escape(token)}"
        match = re.search(pattern, text)
        if match:
            return max(1, int(match.group(1)))
        match = re.search(rf"{re.escape(token)}\s*x?(\d+)", text)
        if match:
            return max(1, int(match.group(1)))
        return 1

    def _extract_remove_items(self, text: str) -> List[int]:
        """Only remove specifically mentioned items, not all by default."""
        ids = []
        text_lower = self._fix_typos(text.lower())
        for item in self.menu:
            name = item["name"].lower()
            if name in text_lower:
                ids.append(item["id"])
        return ids

    def _order_summary(self, prefix: str = "Here is your current order:") -> Dict:
        """Summarize all items currently in the order."""
        if not self.state.items:
            return self._reply("Your order is empty. Ask me to add something first.")
        lines = []
        total = Decimal("0")
        for row in self.state.items:
            qty = int(row["qty"])
            price = Decimal(str(row["price"]))
            subtotal = qty * price
            total += subtotal
            lines.append(f"- {row['name']} x{qty} (₹{subtotal:.0f})")
        summary = f"{prefix}\n" + "\n".join(lines) + f"\nTotal: ₹{total:.0f}. Say 'confirm' to place the order."
        return self._reply(summary)

    def _capture_detail_input(self) -> Dict:
        """Capture required checkout details from the user, stepwise."""
        if not self.state.awaiting_fields:
            return self._order_summary()
        field = self.state.awaiting_fields[0]
        value = self._extract_detail_value(field, self.message)
        if not value:
            return self._reply(f"Please share your {self._field_label(field)}.")
        self.state.details[field] = value
        self.state.awaiting_fields = self.state.awaiting_fields[1:]
        if self.state.awaiting_fields:
            next_field = self.state.awaiting_fields[0]
            return self._reply(f"Thanks! Now share your {self._field_label(next_field)}.")
        return self._finalize_order()

    def _extract_detail_value(self, field: str, message: str) -> Optional[str]:
        """Extract details like phone, name, address stepwise for order processing."""
        text = message.strip()
        lowered = text.lower()
        if field == "phone":
            digits = re.findall(r"\d+", text)
            if digits:
                return digits[0][-10:]
        elif field == "postal_code":
            digits = re.findall(r"\d{4,6}", text)
            if digits:
                return digits[0]
        elif field == "table_number":
            digits = re.findall(r"\d+", text)
            if digits:
                return digits[0]
        elif field == "name":
            match = re.search(r"name\s*is\s*(.+)", lowered)
            if match:
                return match.group(1).title()
            return text.title()
        elif field in {"address_line1", "city"}:
            label = "address" if field == "address_line1" else "city"
            match = re.search(rf"{label}\s*is\s*(.+)", lowered)
            if match:
                return match.group(1).strip().title()
            return text.title()
        else:
            return text
        return None

    def _finalize_order(self) -> Dict:
        """Complete the order and store it in DB, post details gathering and confirmation."""
        if not self.state.items:
            return self._reply("Add at least one item before confirming your order.")
        if not self.request.user.is_authenticated:
            return self._reply("Please log in so I can place the order for you.", require_login=True)
        order_type = self.state.order_type or self._guess_order_type()
        self.state.order_type = order_type
        missing = self._collect_missing_details(order_type)
        if missing:
            self.state.awaiting_fields = missing
            label = self._field_label(missing[0])
            return self._reply(f"I need your {label} to continue.")
        order = self._create_order(order_type)
        self.state.reset()
        return {
            "reply": f"Order #{order.id} is placed! Thank you for ordering; our team will take care of the rest.",
            "order_id": order.id,
        }

    def _guess_order_type(self) -> str:
        text = self.message.lower()
        if any(keyword in text for keyword in self.DELIVERY_KEYWORDS):
            return "DELIVERY"
        return "DINING"

    def _collect_missing_details(self, order_type: str) -> List[str]:
        required = self.DELIVERY_FIELDS if order_type == "DELIVERY" else self.DINING_FIELDS
        supplied = {k for k, v in self.state.details.items() if v}
        return [field for field in required if field not in supplied]

    def _create_order(self, order_type: str) -> Order:
        """Create Order, Items, Address, and Payment in atomic DB transaction."""
        items = self.state.items
        total = sum(Decimal(str(row["price"])) * int(row["qty"]) for row in items)
        customer = self._get_or_create_customer()
        with transaction.atomic():
            order = Order.objects.create(
                customer=customer,
                order_type=order_type,
                table_no=self.state.details.get("table_number", "") if order_type == "DINING" else "",
                total_amount=total,
                status="PENDING_PAYMENT",
            )
            address = None
            if order_type == "DELIVERY":
                address = Address.objects.create(
                    customer=customer,
                    line1=self.state.details.get("address_line1", ""),
                    city=self.state.details.get("city", ""),
                    postal_code=self.state.details.get("postal_code", ""),
                )
                order.delivery_address = address
                order.save(update_fields=["delivery_address"])
            for row in items:
                OrderItem.objects.create(
                    order=order,
                    item_id=row["id"],
                    quantity=int(row["qty"]),
                    unit_price=Decimal(str(row["price"])),
                )
            Payment.objects.create(
                order=order,
                amount=total,
                reference=self.state.details.get("payment_reference", ""),
                status="PENDING",
            )
        return order

    def _get_or_create_customer(self) -> Customer:
        user = self.request.user
        if hasattr(user, "customer_profile") and user.customer_profile:
            customer = user.customer_profile
        else:
            defaults = {
                "name": user.get_full_name() or user.username,
                "phone": self.state.details.get("phone", ""),
                "email": getattr(user, "email", "") or "",
            }
            customer, _ = Customer.objects.get_or_create(user=user, defaults=defaults)
        if self.state.details.get("name"):
            customer.name = self.state.details["name"]
        if self.state.details.get("phone"):
            customer.phone = self.state.details["phone"]
        customer.save(update_fields=["name", "phone"])
        return customer

    def _field_label(self, field: str) -> str:
        labels = {
            "name": "name",
            "phone": "phone number",
            "table_number": "table number",
            "address_line1": "address",
            "city": "city",
            "postal_code": "postal code",
        }
        return labels.get(field, field.replace("_", " "))

    def _reply(self, text: str, require_login: bool = False) -> Dict:
        """Format reply appropriately, optionally prompting for login."""
        payload = {"reply": text}
        if require_login:
            payload["require_login"] = True
        return payload

# -------------------------------------
# End of file: cafe/ai_engine.py
# Comments and logic are designed for maintainability and clear real-life interactions.
# -------------------------------------
